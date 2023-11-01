from abc import abstractmethod
from typing import Any, Optional, OrderedDict, Tuple
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import EmptyPage, Page
from django.db.models import Count, OuterRef, Prefetch, Q, QuerySet, Subquery, Sum
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
from thunderstore.repository.models import Package

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
    Base class for different paginated, filterable package listings.
    """

    page_size = 20

    @abstractmethod
    def _get_base_queryset(self) -> QuerySet[Package]:
        """
        Return QuerySet filtered with endpoint specific operations.

        QuerySet operations shared by all endpoints, like annotations,
        should be implemented in the shared get_queryset().
        """
        raise NotImplementedError(
            "PackageListApiView must implement _get_base_queryset",
        )

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
        params: OrderedDict = qp.validated_data

        # To improve cacheability.
        for value in params.values():
            if isinstance(value, list):
                value.sort()

        package_qs = self.get_queryset()
        package_qs = self._filter_deprecated(params["deprecated"], package_qs)
        package_qs = self._filter_nsfw(params["nsfw"], package_qs)
        package_qs = self._filter_by_categories(params, package_qs)
        package_qs = self._filter_by_section(params.get("section"), package_qs)
        package_qs = self._filter_by_query(params.get("q"), package_qs)
        package_qs = self._order_queryset(params["ordering"], package_qs)
        package_page = self._paginate(params, package_qs)
        serializer = self._serialize_results(params, package_page)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self) -> QuerySet[Package]:
        """
        Implement QuerySet operations shared by all endpoints.
        """

        this_package = Package.objects.filter(pk=OuterRef("pk"))

        return (
            self._get_base_queryset()
            .active()  # type: ignore
            .prefetch_related(
                "community_listings__categories",
                "community_listings__community",
            )
            .select_related("latest", "namespace")
            .annotate(
                download_count=Subquery(
                    this_package.annotate(
                        downloads=Sum("versions__downloads"),
                    ).values("downloads"),
                ),
            )
            .annotate(
                rating_count=Subquery(
                    this_package.annotate(
                        ratings=Count("package_ratings"),
                    ).values("ratings"),
                ),
            )
        )

    def _filter_deprecated(
        self,
        show_deprecated: bool,
        queryset: QuerySet[Package],
    ) -> QuerySet[Package]:
        """
        Deprecated packages are included only if specifically requested.
        """
        if show_deprecated:
            return queryset

        return queryset.exclude(is_deprecated=True)

    def _filter_nsfw(
        self,
        show_nsfw: bool,
        queryset: QuerySet[Package],
    ) -> QuerySet[Package]:
        """
        NSFW packages are included only if specifically requested.
        """
        if show_nsfw:
            return queryset

        return queryset.exclude(community_listings__has_nsfw_content=True)

    def _filter_by_categories(
        self,
        params: OrderedDict,
        queryset: QuerySet[Package],
    ) -> QuerySet[Package]:
        """
        Include only packages (not) belonging to specific categories.

        Multiple categories are OR-joined, i.e. if included_categories
        contain A and B, packages belonging to either will be returned.
        """
        if params["included_categories"]:
            queryset = queryset.exclude(
                ~Q(
                    community_listings__categories__id__in=params[
                        "included_categories"
                    ],
                ),
            )

        if params["excluded_categories"]:
            queryset = queryset.exclude(
                community_listings__categories__id__in=params["excluded_categories"],
            )

        return queryset

    def _filter_by_section(
        self,
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

        if required:
            queryset = queryset.exclude(
                ~Q(community_listings__categories__pk__in=required),
            )

        if excluded:
            queryset = queryset.exclude(community_listings__categories__pk__in=excluded)

        return queryset

    def _filter_by_query(
        self,
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

    def _serialize_results(
        self,
        params: OrderedDict,
        package_page: Page,
    ) -> PackageListResponseSerializer:
        """
        Format results to transportation.
        """
        packages = [
            {
                "categories": p.community_listings.all()[0].categories.all(),
                "community_identifier": p.community_listings.all()[
                    0
                ].community.identifier,
                "description": p.latest.description,
                "download_count": p.download_count,
                "icon_url": p.latest.icon.url if bool(p.latest.icon) else None,
                "is_deprecated": p.is_deprecated,
                "is_nsfw": p.community_listings.all()[0].has_nsfw_content,
                "is_pinned": p.is_pinned,
                "last_updated": p.date_updated,
                "namespace": p.namespace.name,
                "name": p.name,
                "rating_count": p.rating_count,
                "size": p.latest.file_size,
            }
            for p in package_page.object_list
        ]

        (prev_url, next_url) = self._get_sibling_pages(params, package_page)

        return PackageListResponseSerializer(
            {
                "count": package_page.paginator.count,
                "previous": prev_url,
                "next": next_url,
                "results": packages,
            },
        )

    def _get_full_cache_vary(self, params: OrderedDict) -> str:
        """
        Return cache key for CachedPaginator.
        """
        cache_vary = self._get_paginator_cache_vary_prefix()
        cache_vary += f".{params['deprecated']}"
        cache_vary += f".{params['nsfw']}"
        cache_vary += f".{sorted(params['included_categories'])}"
        cache_vary += f".{sorted(params['excluded_categories'])}"
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


def get_community_package_queryset(community: Community) -> QuerySet[Package]:
    """
    Create base QuerySet for community scoped PackageListAPIViews.
    """
    review_statuses = [PackageListingReviewStatus.approved]

    if not community.require_package_listing_approval:
        review_statuses.append(PackageListingReviewStatus.unreviewed)

    # Ensure each package.community_listings QuerySet will include
    # only listings related to current community.
    community_listings = Prefetch(
        "community_listings",
        community.package_listings.all(),
    )

    return (
        Package.objects.prefetch_related(community_listings)
        .exclude(~Q(community_listings__review_status__in=review_statuses))
        .exclude(~Q(community_listings__community__pk=community.pk))
    )


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
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def _get_base_queryset(self) -> QuerySet[Package]:
        """
        Return QuerySet filtered with endpoint specific operations.
        """
        community_id = self.kwargs["community_id"]
        community = get_object_or_404(Community, identifier=community_id)

        return get_community_package_queryset(community)

    def _get_paginator_cache_key(self):
        return "api.cyberstorm.package.community"

    def _get_paginator_cache_vary_prefix(self):
        return self.kwargs["community_id"]

    def _get_request_path(self) -> str:
        return reverse(
            "api:cyberstorm:cyberstorm.package.community",
            kwargs={"community_id": self.kwargs["community_id"]},
        )
