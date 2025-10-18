from typing import Optional, OrderedDict

from django.core.paginator import EmptyPage, Page
from django.db.models import Count, Prefetch, Q, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import Community, PackageListingSection
from thunderstore.frontend.api.experimental.serializers.views import (
    CommunityPackageListSerializer,
    PackageCategorySerializer,
    PackageSearchQueryParameterSerializer,
)
from thunderstore.repository.models import Package


class CommunityPackageListApiView(APIView):
    """
    Return paginated list of community's packages.
    """

    permission_classes = []

    @swagger_auto_schema(
        responses={200: CommunityPackageListSerializer()},
        operation_id="experimental.frontend.community.packages",
        deprecated=True,
        tags=["experimental"],
    )
    def get(self, request: HttpRequest, community_identifier: str) -> HttpResponse:
        communities = Community.objects.prefetch_related("package_categories")
        community = get_object_or_404(communities, identifier=community_identifier)

        qp = PackageSearchQueryParameterSerializer(data=request.query_params)
        if not qp.is_valid():
            return Response(qp.errors, status=status.HTTP_400_BAD_REQUEST)

        params: OrderedDict = qp.validated_data
        package_qs = self.get_queryset(community)
        package_qs = self.filter_deprecated(params["deprecated"], package_qs)
        package_qs = self.filter_nsfw(params["nsfw"], package_qs)
        package_qs = self.filter_by_categories(params, package_qs)
        package_qs = self.filter_by_section(params.get("section"), package_qs)
        package_qs = self.filter_by_query(params.get("q"), package_qs)
        package_qs = self.order_queryset(params["ordering"], package_qs)
        package_page = self.paginate(params, package_qs)
        serializer = self.serialize_results(community, package_page)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_full_cache_vary(self, params: OrderedDict) -> str:
        """
        Return cache key for CachedPaginator.
        """
        cache_vary = self.kwargs["community_identifier"]
        cache_vary += f".{params['deprecated']}"
        cache_vary += f".{params['nsfw']}"
        cache_vary += f".{sorted(params['included_categories'])}"
        cache_vary += f".{sorted(params['excluded_categories'])}"
        cache_vary += f".{params.get('section', '-')}"
        cache_vary += f".{params.get('q', '-')}"
        cache_vary += f".{params['ordering']}"
        cache_vary += f".{params['page']}"
        return cache_vary

    def get_queryset(self, community: Community) -> QuerySet[Package]:
        """
        Return base QuerySet before request-specific operations.
        """
        review_statuses = [PackageListingReviewStatus.approved]

        if not community.require_package_listing_approval:
            review_statuses.append(PackageListingReviewStatus.unreviewed)

        # Ensure each package.community_listings QuerySet will include
        # only listings related to current community.
        community_listings = Prefetch(
            "community_listings", community.package_listings.all()
        )

        return (
            Package.objects.active()
            .filter(
                community_listings__community__pk=community.pk,
                community_listings__review_status__in=review_statuses,
            )
            .prefetch_related(
                community_listings,
                "community_listings__categories",
                "community_listings__community",
            )
            .select_related("latest", "namespace", "owner")
            .annotate(total_downloads=Sum("versions__downloads"))
            .annotate(total_rating=Count("package_ratings"))
        )

    def filter_deprecated(
        self, show_deprecated: bool, queryset: QuerySet[Package]
    ) -> QuerySet[Package]:
        """
        Deprecated packages are included only if specifically requested.
        """
        if show_deprecated:
            return queryset

        return queryset.exclude(is_deprecated=True)

    def filter_nsfw(
        self, show_nsfw: bool, queryset: QuerySet[Package]
    ) -> QuerySet[Package]:
        """
        NSFW packages are included only if specifically requested.
        """
        if show_nsfw:
            return queryset

        return queryset.exclude(community_listings__has_nsfw_content=True)

    def filter_by_categories(
        self, params: OrderedDict, queryset: QuerySet[Package]
    ) -> QuerySet[Package]:
        """
        Include only packages (not) belonging to specific categories.

        Multiple categories are OR-joined, i.e. if included_categories
        contain A and B, packages belonging to either will be returned.
        """
        if params["included_categories"]:
            queryset = queryset.exclude(
                ~Q(
                    community_listings__categories__slug__in=params[
                        "included_categories"
                    ]
                )
            )

        if params["excluded_categories"]:
            queryset = queryset.exclude(
                community_listings__categories__slug__in=params["excluded_categories"]
            )

        return queryset

    def filter_by_section(
        self, section_slug: Optional[str], queryset: QuerySet[Package]
    ) -> QuerySet[Package]:
        """
        PackageListingSections can be used as shortcut for multiple
        category filters.
        """
        if not section_slug:
            return queryset

        try:
            section = PackageListingSection.objects.prefetch_related(
                "require_categories", "exclude_categories"
            ).get(slug=section_slug)
        except PackageListingSection.DoesNotExist:
            required = []
            excluded = []
        else:
            required = section.require_categories.values_list("pk", flat=True)
            excluded = section.exclude_categories.values_list("pk", flat=True)

        if required:
            queryset = queryset.exclude(
                ~Q(community_listings__categories__pk__in=required)
            )

        if excluded:
            queryset = queryset.exclude(community_listings__categories__pk__in=excluded)

        return queryset

    def filter_by_query(
        self, query: Optional[str], queryset: QuerySet[Package]
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

    def order_queryset(
        self, ordering: str, queryset: QuerySet[Package]
    ) -> QuerySet[Package]:
        """
        Order results in requested order, defaulting to latest update.
        """
        order_arg = {
            "last-updated": "-date_updated",
            "most-downloaded": "-total_downloads",
            "newest": "-date_created",
            "top-rated": "-total_rating",
        }.get(ordering, "-date_updated")

        return queryset.order_by("-is_pinned", "is_deprecated", order_arg)

    def paginate(self, params: OrderedDict, queryset: QuerySet[Package]) -> Page:
        """
        Slice queryset based on the requested page.
        """
        paginator = CachedPaginator(
            queryset,
            24,  # Should be divisible by 3 and 4
            cache_key="frontend.community_package_list.paginator",
            cache_vary=self.get_full_cache_vary(params),
            cache_bust_condition=CacheBustCondition.any_package_updated,
        )

        # PageNotAnInteger error won't be raised here since deserializer
        # has already checked that the page parameter is an integer.
        try:
            page = paginator.page(params["page"])
        except EmptyPage:
            raise ParseError("Page index error: no results on requested page")

        return page

    def serialize_results(
        self, community: Community, package_page: Page
    ) -> CommunityPackageListSerializer:
        """
        Format results to transportation.
        """
        packages = [
            {
                "categories": [
                    PackageCategorySerializer(c).data
                    for c in p.community_listings.all()[0].categories.visible()
                ],
                "community_identifier": community.identifier,
                "community_name": community.name,
                "description": p.latest.description,
                "download_count": p.total_downloads,
                "image_src": p.latest.icon.url if bool(p.latest.icon) else None,
                "is_deprecated": p.is_deprecated,
                "is_nsfw": p.community_listings.all()[0].has_nsfw_content,
                "is_pinned": p.is_pinned,
                "last_updated": p.date_updated,
                "namespace": p.namespace.name,
                "package_name": p.name,
                "rating_score": p.total_rating,
                "team_name": p.owner.name,
            }
            for p in package_page.object_list
        ]

        return CommunityPackageListSerializer(
            {
                "bg_image_src": community.background_image_url,
                "cover_image_src": community.cover_image_url,
                "categories": [
                    PackageCategorySerializer(c).data
                    for c in community.package_categories.visible()
                ],
                "community_name": community.name,
                "packages": packages,
                "has_more_pages": package_page.has_next(),
            },
        )
