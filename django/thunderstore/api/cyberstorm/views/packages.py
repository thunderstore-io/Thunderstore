from abc import abstractmethod
from typing import Any, List, Optional, OrderedDict, Tuple
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import EmptyPage, Page
from django.db.models import Count, OuterRef, Q, QuerySet, Subquery, Sum
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.exceptions import ParseError
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers import CyberstormPackagePreviewSerializer
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import Community, PackageListingSection
from thunderstore.repository.models import Namespace, Package

# Keys are values expected in requests, values are args for .order_by().
ORDER_ARGS = {
    "last-updated": "-date_updated",
    "most-downloaded": "-download_count",  # annotated field
    "newest": "-date_created",
    "top-rated": "-rating_count",  # annotated field
}


class PackageListRequestSerializer(serializers.Serializer):
    """
    For deserializing the query parameters used in package filtering.
    """

    deprecated = serializers.BooleanField(default=False)
    excluded_categories = serializers.ListField(
        child=serializers.IntegerField(),
        default=[],
    )
    included_categories = serializers.ListField(
        child=serializers.IntegerField(),
        default=[],
    )
    nsfw = serializers.BooleanField(default=False)
    ordering = serializers.ChoiceField(
        choices=list(ORDER_ARGS.keys()),
        default="last-updated",
    )
    page = serializers.IntegerField(default=1, min_value=1)
    q = serializers.CharField(required=False)
    section = serializers.UUIDField(required=False)


class PackageListResponseSerializer(serializers.Serializer):
    """
    Matches DRF's PageNumberPagination response.
    """

    count = serializers.IntegerField(min_value=0)
    previous = serializers.CharField(allow_null=True)
    next = serializers.CharField(allow_null=True)  # noqa: A003
    results = CyberstormPackagePreviewSerializer(many=True)


class BasePackageListApiView(ListAPIView):
    """
    Base class for community-scoped, paginated, filterable package listings.

    Classes implementing this base class should receive `community_id`
    url parameter and implement the abstract methods listed below.
    """

    page_size = 20

    @abstractmethod
    def _get_paginator_cache_key(self) -> str:
        """
        Return cache_key argument for CachedPaginator initialization.
        """
        raise NotImplementedError(
            "PackageListApiView must implement _get_paginator_cache_key",
        )

    @abstractmethod
    def _get_paginator_cache_vary_prefix(self) -> str:
        """
        Return endpoint and URL parameter specific string.

        This is used as a part to create the cache_vary argument for
        CachedPaginator initialization. Do not include query parameter
        related information in this part.
        """
        raise NotImplementedError(
            "PackageListApiView must implement _get_paginator_cache_vary_prefix",
        )

    @abstractmethod
    def _get_request_path(self) -> str:
        """
        Return path part of URL to access the endpoint
        """
        raise NotImplementedError(
            "PackageListApiView must implement _get_request_path",
        )

    def get(self, request, *args, **kwargs):
        qp = PackageListRequestSerializer(data=request.query_params)
        qp.is_valid(raise_exception=True)
        params = qp.validated_data

        # To improve cacheability.
        for value in params.values():
            if isinstance(value, list):
                value.sort()

        package_qs = self._get_package_queryset()
        package_qs = filter_deprecated(params["deprecated"], package_qs)
        package_qs = filter_nsfw(params["nsfw"], package_qs)
        package_qs = filter_in_categories(params["included_categories"], package_qs)
        package_qs = filter_not_in_categories(params["excluded_categories"], package_qs)
        package_qs = filter_by_section(params.get("section"), package_qs)
        package_qs = filter_by_query(params.get("q"), package_qs)
        package_qs = self._annotate_queryset(package_qs)
        package_qs = self._order_queryset(params["ordering"], package_qs)

        package_page = self._paginate(params, package_qs)
        (prev_url, next_url) = self._get_sibling_pages(params, package_page)
        packages = self._get_packages_dicts(package_page)

        serializer = PackageListResponseSerializer(
            {
                "count": package_page.paginator.count,
                "previous": prev_url,
                "next": next_url,
                "results": packages,
            },
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_package_queryset(self) -> QuerySet[Package]:
        community_id = self.kwargs["community_id"]
        community = get_object_or_404(Community, identifier=community_id)
        queryset = get_community_package_queryset(community)

        return filter_by_review_status(
            community.require_package_listing_approval,
            queryset,
        )

    def _annotate_queryset(self, queryset: QuerySet[Package]) -> QuerySet[Package]:
        """
        Add annotations required to serialize the results.
        """

        this_package = Package.objects.filter(pk=OuterRef("pk"))

        return queryset.annotate(
            download_count=Subquery(
                this_package.annotate(
                    downloads=Sum("versions__downloads"),
                ).values("downloads"),
            ),
        ).annotate(
            rating_count=Subquery(
                this_package.annotate(
                    ratings=Count("package_ratings"),
                ).values("ratings"),
            ),
        )

    def _order_queryset(
        self,
        ordering: str,
        queryset: QuerySet[Package],
    ) -> QuerySet[Package]:
        """
        Order results in requested order, defaulting to latest update.
        """
        return queryset.order_by(
            "-is_pinned",
            "is_deprecated",
            ORDER_ARGS[ordering],
            "-date_updated",
            "-pk",
        )

    def _paginate(self, params: OrderedDict, queryset: QuerySet[Package]) -> Page:
        """
        Slice queryset based on the requested page.
        """
        paginator = CachedPaginator(
            queryset,
            self.page_size,
            cache_key=self._get_paginator_cache_key(),
            cache_vary=self._get_full_cache_vary(params),
            cache_bust_condition=CacheBustCondition.any_package_updated,
        )

        try:
            page = paginator.page(params["page"])
        except EmptyPage:
            raise ParseError("Page index error: no results on requested page")

        return page

    def _get_packages_dicts(self, package_page: Page):
        community_id = self.kwargs["community_id"]
        packages = []

        for p in package_page.object_list:
            listing = p.community_listings.get(community__identifier=community_id)

            packages.append(
                {
                    "categories": listing.categories.all(),
                    "community_identifier": community_id,
                    "description": p.latest.description,
                    "download_count": p.download_count,
                    "icon_url": p.latest.icon.url if bool(p.latest.icon) else None,
                    "is_deprecated": p.is_deprecated,
                    "is_nsfw": listing.has_nsfw_content,
                    "is_pinned": p.is_pinned,
                    "last_updated": p.date_updated,
                    "namespace": p.namespace.name,
                    "name": p.name,
                    "rating_count": p.rating_count,
                    "size": p.latest.file_size,
                },
            )

        return packages

    def _get_full_cache_vary(self, params: OrderedDict) -> str:
        """
        Return cache key for CachedPaginator.
        """
        cache_vary = self._get_paginator_cache_vary_prefix()
        cache_vary += f".{params['deprecated']}"
        cache_vary += f".{params['nsfw']}"
        cache_vary += f".{params['included_categories']}"
        cache_vary += f".{params['excluded_categories']}"
        cache_vary += f".{params.get('section', '-')}"
        cache_vary += f".{params.get('q', '-')}"
        cache_vary += f".{params['ordering']}"
        cache_vary += f".{params['page']}"
        cache_vary += f".{self.page_size}"
        return cache_vary

    def _get_sibling_pages(
        self,
        params: OrderedDict,
        package_page: Page,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Return the URLs to previous and next pages of this result set.
        """
        base_url = (
            f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{self._get_request_path()}"
        )
        previous_url = None
        next_url = None

        if package_page.has_previous():
            params["page"] -= 1
            previous_url = f"{base_url}?{urlencode(params, doseq=True)}"
            params["page"] += 1

        if package_page.has_next():
            params["page"] += 1
            next_url = f"{base_url}?{urlencode(params, doseq=True)}"
            params["page"] -= 1

        return (previous_url, next_url)


class CommunityPackageListApiView(BasePackageListApiView):
    """
    Community-scoped package list.
    """

    @conditional_swagger_auto_schema(
        query_serializer=PackageListRequestSerializer,
        responses={200: PackageListResponseSerializer()},
        operation_id="api_cyberstorm_package_community",
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _get_paginator_cache_key(self):
        return "api.cyberstorm.package.community"

    def _get_paginator_cache_vary_prefix(self):
        return self.kwargs["community_id"]

    def _get_request_path(self) -> str:
        return reverse(
            "api:cyberstorm:cyberstorm.package.community",
            kwargs={"community_id": self.kwargs["community_id"]},
        )


class NamespacePackageListApiView(BasePackageListApiView):
    """
    Community & Namespace-scoped package list.
    """

    @conditional_swagger_auto_schema(
        query_serializer=PackageListRequestSerializer,
        responses={200: PackageListResponseSerializer()},
        operation_id="api_cyberstorm_package_community_namespace",
        tags=["cyberstorm"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def _get_package_queryset(self) -> QuerySet[Package]:
        namespace_id = self.kwargs["namespace_id"]
        namespace = get_object_or_404(Namespace, name__iexact=namespace_id)

        community_scoped_qs = super()._get_package_queryset()
        return community_scoped_qs.exclude(~Q(namespace=namespace))

    def _get_paginator_cache_key(self):
        return "api.cyberstorm.package.community.namespace"

    def _get_paginator_cache_vary_prefix(self):
        return f"{self.kwargs['community_id']}/{self.kwargs['namespace_id']}"

    def _get_request_path(self) -> str:
        return reverse(
            "api:cyberstorm:cyberstorm.package.community.namespace",
            kwargs={
                "community_id": self.kwargs["community_id"],
                "namespace_id": self.kwargs["namespace_id"],
            },
        )


def get_community_package_queryset(community: Community) -> QuerySet[Package]:
    """
    Create base QuerySet for community scoped PackageListAPIViews.
    """

    return (
        Package.objects.active()  # type: ignore
        .select_related("latest", "namespace")
        .prefetch_related(
            "community_listings__categories",
            "community_listings__community",
        )
        .exclude(~Q(community_listings__community__pk=community.pk))
    )


def filter_deprecated(
    show_deprecated: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    if show_deprecated:
        return queryset

    return queryset.exclude(is_deprecated=True)


def filter_nsfw(
    show_nsfw: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    if show_nsfw:
        return queryset

    return queryset.exclude(community_listings__has_nsfw_content=True)


def filter_in_categories(
    category_ids: List[int],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Include only packages belonging to specific categories.

    Multiple categories are OR-joined, i.e. if category_ids contain A
    and B, packages belonging to either will be returned.
    """
    if not category_ids:
        return queryset

    return queryset.exclude(
        ~Q(community_listings__categories__id__in=category_ids),
    )


def filter_not_in_categories(
    category_ids: List[int],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Exclude packages belonging to specific categories.

    Multiple categories are OR-joined, i.e. if category_ids contain A
    and B, packages belonging to either will be rejected.
    """
    if not category_ids:
        return queryset

    return queryset.exclude(
        community_listings__categories__id__in=category_ids,
    )


def filter_by_section(
    section_uuid: Optional[str],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    PackageListingSections can be used as shortcut for multiple
    category filters.
    """
    if not section_uuid:
        return queryset

    try:
        section = PackageListingSection.objects.prefetch_related(
            "require_categories",
            "exclude_categories",
        ).get(uuid=section_uuid)
    except PackageListingSection.DoesNotExist:
        required = []
        excluded = []
    else:
        required = section.require_categories.values_list("pk", flat=True)
        excluded = section.exclude_categories.values_list("pk", flat=True)

    queryset = filter_in_categories(required, queryset)
    return filter_not_in_categories(excluded, queryset)


def filter_by_query(
    query: Optional[str],
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    """
    Filter packages by free text search.
    """
    if not query:
        return queryset

    search_fields = ("name", "owner__name", "latest__description")
    icontains_query = Q()
    parts = [x for x in query.split(" ") if x]

    for part in parts:
        for field in search_fields:
            icontains_query &= ~Q(**{f"{field}__icontains": part})

    return queryset.exclude(icontains_query).distinct()


def filter_by_review_status(
    require_approval: bool,
    queryset: QuerySet[Package],
) -> QuerySet[Package]:
    review_statuses = [PackageListingReviewStatus.approved]

    if not require_approval:
        review_statuses.append(PackageListingReviewStatus.unreviewed)

    return queryset.exclude(
        ~Q(community_listings__review_status__in=review_statuses),
    )
