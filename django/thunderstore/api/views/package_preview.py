from itertools import chain
import math

from typing import OrderedDict

from django.core.paginator import EmptyPage, Page
from django.db.models import Count, Q, QuerySet, Sum, Case, When, Value
from django.db.models import Lookup, CharField
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from thunderstore.community.models.package_category import PackageCategory
from thunderstore.community.models.package_listing import PackageListing

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.models import PackageListingSection
from thunderstore.api.serializers.package import (
    CommunityPackageListCyberstormSerializer,
    PackageCategoryCyberstormSerializer,
    PackageSearchQueryParameterCyberstormSerializer,
)

class LowerContainedBy(Lookup):
    lookup_name = 'icontained_by'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"LOWER({rhs}) LIKE '%%' || LOWER({lhs}) || '%%'", params

CharField.register_lookup(LowerContainedBy)

class PackagePreviewAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CommunityPackageListCyberstormSerializer()},
        operation_id="experimental.frontend.community.packages",
    )
    def get(
        self,
        request: HttpRequest,
    ) -> HttpResponse:

        qp = PackageSearchQueryParameterCyberstormSerializer(data=request.query_params)
        if not qp.is_valid():
            return Response(qp.errors, status=status.HTTP_400_BAD_REQUEST)

        params: OrderedDict = qp.validated_data
        listings_qs = self.get_queryset(params)
        listings_qs = self.order_queryset(params["ordering"], listings_qs)
        categories = PackageCategory.objects.filter(pk__in=listings_qs.aggregate(arr=ArrayAgg("categories", distinct=True))["arr"])
        listings_page = self.paginate(params, listings_qs, params["page_size"])
        listing_count = len(listings_qs)
        serializer = self.serialize_results(listings_page, categories, listing_count, params["page_size"])

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_full_cache_vary(self, params: OrderedDict) -> str:
        cache_vary = "package_cache_key"
        if params.get("community_identifier", None):
            cache_vary += f".{params['community_identifier']}"
        if params.get("namespace_identifier", None):
            cache_vary += f".{params['namespace_identifier']}"
        if params.get("team_identifier", None):
            cache_vary += f".{params['team_identifier']}"
        if params.get("user_identifier", None):
            cache_vary += f".{params['user_identifier']}"
        if params.get("package_identifier", None):
            cache_vary += f".{params['package_identifier']}"
        cache_vary += f".{params['deprecated']}"
        cache_vary += f".{params['nsfw']}"
        cache_vary += f".{sorted(params['included_categories'])}"
        cache_vary += f".{sorted(params['excluded_categories'])}"
        cache_vary += f".{params.get('section', '-')}"
        cache_vary += f".{params.get('q', '-')}"
        cache_vary += f".{params['ordering']}"
        cache_vary += f".{params['page']}"
        cache_vary += f".{params['page_size']}"
        return cache_vary

    def get_queryset(self, params) -> QuerySet[PackageListing]:
        # Prep Q objects
        filter_q = Q()
        exclude_q = Q()

        # Add majority of filters
        if params.get("community_identifier", None):
            filter_q.add(Q(community__identifier=params["community_identifier"]), Q.AND)

        if params.get("namespace_identifier", None):
            filter_q.add(Q(package__namespace__name=params["namespace_identifier"]), Q.AND)

        if params.get("team_identifier", None):
            filter_q.add(Q(package__owner__name=params["team_identifier"]), Q.AND)

        if params.get("user_identifier", None):
            filter_q.add(Q(package__owner__members__user__username__icontains=params["user_identifier"]), Q.AND)

        if params.get("package_identifier", None):
            filter_q.add(Q(package__name=params["package_identifier"]), Q.AND)

        if params.get("deprecated", None):
            filter_q.add(Q(package__is_deprecated=params["deprecated"]), Q.AND)

        if params.get("nsfw", None):
            filter_q.add(Q(has_nsfw_content=params["nsfw"]), Q.AND)

        if params.get("q", None):
            icontains_query = Q()
            parts = [x for x in params["q"].split(" ") if x]

            for part in parts:
                for field in ("package__name", "package__owner__name", "package__latest__description"):
                    icontains_query &= ~Q(**{f"{field}__icontains": part})
            exclude_q.add(icontains_query, Q.AND)

        # Add category filters/excludes
        included = []
        excluded = []
        if params.get("section", None):
            try:
                section = PackageListingSection.objects.prefetch_related(
                    "require_categories", "exclude_categories"
                ).get(slug=params["section"])
            except PackageListingSection.DoesNotExist:
                pass
            else:
                [included.append(s.slug) for s in section.require_categories.all()]
                [excluded.append(s.slug) for s in section.exclude_categories.all()]

        if params.get("included_categories", None):
            included = list(chain(included, params["included_categories"]))

        if params.get("excluded_categories", None):
            excluded = list(chain(excluded, params["excluded_categories"]))

        if len(included) > 0:
            included_cats_q = Q()
            for cat in sorted(set(included)):
                included_cats_q.add(Q(categories__slug__icontains=cat), Q.OR)
            filter_q.add(included_cats_q, Q.AND)

        if len(excluded) > 0:
            excluded_cats_q = Q()
            for cat in sorted(set(excluded)):
                excluded_cats_q.add(Q(categories__slug__icontains=cat), Q.OR)
            exclude_q.add(excluded_cats_q, Q.AND)

        return (
            PackageListing.objects.filter(
                review_status__icontained_by=Case(
                    When(Q(community__require_package_listing_approval=True), then=Value("approved")),
                    default=Value("unreviewed rejected")
                )
            )
            .filter(filter_q)
            .exclude(exclude_q)
            .distinct()
            .prefetch_related(
                "categories",
                "community",
            )
            .select_related("package__latest", "package__namespace", "package__owner")
            .annotate(package_total_downloads=Sum("package__versions__downloads"))
            .annotate(package_total_rating=Count("package__package_ratings"))
        )

    def order_queryset(
        self, ordering: str, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        order_arg = {
            "last-updated": "-package__date_updated",
            "most-downloaded": "-package_total_downloads",
            "newest": "-package__date_created",
            "top-rated": "-package_total_rating",
        }.get(ordering, "-date_updated")

        return queryset.order_by("-package__is_pinned", "package__is_deprecated", order_arg)

    def paginate(self, params: OrderedDict, queryset: QuerySet[PackageListing], page_size: int) -> Page:
        paginator = CachedPaginator(
            queryset,
            page_size,
            cache_key="api.package_previews.paginator",
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
        self, listings_page: Page, categories: QuerySet[PackageCategory], categories_count: int, page_size: int
    ) -> CommunityPackageListCyberstormSerializer:
        packages = [
            {
                "name": listing.package.name,
                "namespace": listing.package.namespace.name,
                "community": listing.community.identifier,
                "shortDescription": listing.package.latest.description,
                "imageSource": listing.package.latest.icon.url if bool(listing.package.latest.icon) else None,
                "downloadCount": listing.package_total_downloads,
                "likes": listing.package_total_rating,
                "size": listing.package.latest.file_size,
                "author": listing.package.owner.name,
                "lastUpdated": listing.package.date_updated,
                "isPinned": listing.package.is_pinned,
                "isNsfw": listing.has_nsfw_content,
                "isDeprecated": listing.package.is_deprecated,
                "categories": [
                    PackageCategoryCyberstormSerializer(c).data
                    for c in listing.categories.all()
                ],
            }
            for listing in listings_page.object_list
        ]

        return CommunityPackageListCyberstormSerializer(
            {
                "categories": [
                    PackageCategoryCyberstormSerializer(c).data
                    for c in categories
                ],
                "packages": packages,
                "pagesBehind": math.floor((listings_page.start_index()/page_size)),
                "pagesAhead": math.ceil(((categories_count-listings_page.end_index())/page_size)),
                "pagesHasPrevious": listings_page.has_previous(),
                "pagesHasNext": listings_page.has_next(),
            },
        )
