from typing import OrderedDict

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import (
    Case,
    CharField,
    Count,
    Lookup,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers.package import (
    PackageCategorySerializerCyberstorm,
    PackageListSearchQueryParameterSerializerCyberstorm,
    PackageListSerializerCyberstorm,
    PackageSerializerCyberstorm,
)
from thunderstore.community.models import PackageListingSection
from thunderstore.community.models.package_category import PackageCategory
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models.package import Package


class PackagesPaginator(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
    page_size = 20

    def get_paginated_response(self, listings, categories):
        return Response(
            OrderedDict(
                [
                    ("current", self.page.number),
                    ("final", self.page.paginator.num_pages),
                    ("total", self.page.paginator.count),
                    ("count", len(listings)),
                    ("categories", categories),
                    ("results", listings),
                ]
            )
        )


class PackageListAPIView(GenericAPIView):
    permission_classes = []
    serializer_class = PackageListSerializerCyberstorm
    pagination_class = PackagesPaginator

    @swagger_auto_schema(
        responses={200: PackageListSerializerCyberstorm()},
        operation_id="cyberstorm.packages",
    )
    def get(
        self,
        request: HttpRequest,
    ) -> HttpResponse:

        qp = PackageListSearchQueryParameterSerializerCyberstorm(
            data=request.query_params
        )
        qp.is_valid(raise_exception=True)

        params: OrderedDict = qp.validated_data
        listings_qs = self.get_queryset(params)
        listings_qs = self.order_queryset(
            params.get("ordering", "last-updated"), listings_qs
        )
        categories = PackageCategory.objects.filter(
            community__pk__in=listings_qs.aggregate(
                arr=ArrayAgg("community", distinct=True)
            )["arr"]
        )

        serializer = self.paginate_and_serialize_results(listings_qs, categories)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self, params) -> QuerySet[PackageListing]:
        # Prep Q objects
        filter_q_object = Q()
        exclude_q_object = Q()

        exclude_q_object |= Q(review_status="rejected")

        filter_q_object &= Q(
            review_status__in=[
                Case(
                    When(
                        Q(community__require_package_listing_approval=False),
                        then=Value("unreviewed"),
                    )
                ),
                "approved",
            ]
        )

        # Add majority of filters
        include_queries = [
            ("community_id", Q(community__identifier=params["community_id"])),
            ("namespace", Q(package__namespace__name=params["namespace"])),
            ("team_id", Q(package__owner__name=params["team_id"])),
            (
                "user_id",
                Q(package__owner__members__user__username__exact=params["user_id"]),
            ),
            ("package_id", Q(package__name=params["package_id"])),
        ]
        [
            filter_q_object.add(query, Q.AND) if params.get(key, False) else False
            for key, query in include_queries
        ]

        # Exclude these by default if param not present
        exlcude_queries = [
            ("include_deprecated", Q(package__is_deprecated=True)),
            ("include_nsfw", Q(has_nsfw_content=True)),
        ]
        [
            exclude_q_object.add(query, Q.OR) if not params.get(key, None) else False
            for key, query in exlcude_queries
        ]

        # Search param
        if params.get("q", None):
            icontains_query = Q()
            parts = [x for x in params["q"].split(" ") if x]

            for part in parts:
                for field in (
                    "package__name",
                    "package__owner__name",
                    "package__latest__description",
                ):
                    icontains_query &= ~Q(**{f"{field}__icontains": part})
            exclude_q_object.add(icontains_query, Q.OR)

        # Add category filters/excludes
        included_categories = []
        excluded_categories = []

        if params.get("section", None):
            section = get_object_or_404(
                PackageListingSection.objects.prefetch_related(
                    "require_categories", "exclude_categories"
                ),
                slug=params["section"],
            )
            [
                included_categories.append(s.slug)
                for s in section.require_categories.all()
            ]
            [
                excluded_categories.append(s.slug)
                for s in section.exclude_categories.all()
            ]

        included_categories = set(
            included_categories + params.get("included_categories", [])
        )
        excluded_categories = set(
            excluded_categories + params.get("excluded_categories", [])
        )

        if len(included_categories) > 0:
            included_cats_q = Q()
            for cat in sorted(included_categories):
                included_cats_q.add(Q(categories__slug__exact=cat), Q.OR)
            filter_q_object &= included_cats_q

        if len(excluded_categories) > 0:
            excluded_cats_q = Q()
            for cat in sorted(excluded_categories):
                excluded_cats_q.add(Q(categories__slug__exact=cat), Q.OR)
            exclude_q_object |= excluded_cats_q

        return (
            PackageListing.objects.active()
            .filter(filter_q_object)
            .exclude(exclude_q_object)
            .distinct()
            .prefetch_related(
                "categories",
                "community",
            )
            .select_related("package__latest", "package__namespace", "package__owner")
            .annotate(
                package_total_downloads=Coalesce(
                    Subquery(
                        Package.objects.filter(pk=OuterRef("package__pk")).values(
                            downloads=Sum("versions__downloads")
                        )[:1]
                    ),
                    Value(0),
                )
            )
            .annotate(
                package_total_rating=Count("package__package_ratings", distinct=True)
            )
        )

    def order_queryset(
        self, ordering: str, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        order_arg = {
            "last-updated": "-package__date_updated",
            "most-downloaded": "-package_total_downloads",
            "newest": "-package__date_created",
            "top-rated": "-package_total_rating",
        }.get(ordering, "-package__date_updated")

        return queryset.order_by(
            "-package__is_pinned", "package__is_deprecated", order_arg
        )

    def paginate_and_serialize_results(
        self,
        listings_q: QuerySet[PackageListing],
        categories: QuerySet[PackageCategory],
    ) -> PackageListSerializerCyberstorm:

        page_q = self.paginate_queryset(listings_q)
        packages = [
            PackageSerializerCyberstorm(
                {
                    "name": listing.package.name,
                    "namespace": listing.package.namespace.name,
                    "community": listing.community.identifier,
                    "short_description": listing.package.latest.description,
                    "image_source": listing.package.latest.icon.url
                    if bool(listing.package.latest.icon)
                    else None,
                    "download_count": listing.package_total_downloads,
                    "likes": listing.package_total_rating,
                    "size": listing.package.latest.file_size,
                    "author": listing.package.owner.name,
                    "last_updated": listing.package.date_updated,
                    "is_pinned": listing.package.is_pinned,
                    "is_nsfw": listing.has_nsfw_content,
                    "is_deprecated": listing.package.is_deprecated,
                    "categories": [
                        PackageCategorySerializerCyberstorm(c).data
                        for c in listing.categories.all()
                    ],
                }
            ).data
            for listing in page_q
        ]

        return self.paginator.get_paginated_response(
            packages, [PackageCategorySerializerCyberstorm(c).data for c in categories]
        )
