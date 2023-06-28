from typing import OrderedDict

from django.db.models import BooleanField, Case, Count, Q, QuerySet, Sum, When
from django.db.models.functions import Lower
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers import (
    CommunityListQueryParameterSerializerCyberstorm,
    CommunityListSerializerCyberstorm,
)
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import Community


class CommunityPaginator(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
    page_size = 20

    def get_paginated_response(self, listings):
        return Response(
            OrderedDict(
                [
                    ("current", self.page.number),
                    ("final", self.page.paginator.num_pages),
                    ("total", self.page.paginator.count),
                    ("count", len(listings)),
                    ("results", listings),
                ]
            )
        )


class CommunityListAPIView(GenericAPIView):
    permission_classes = []
    serializer_class = CommunityListSerializerCyberstorm
    pagination_class = CommunityPaginator

    @swagger_auto_schema(
        responses={200: CommunityListSerializerCyberstorm()},
        operation_id="cyberstorm.communities",
    )
    def get(
        self,
        request: HttpRequest,
    ) -> HttpResponse:

        qp = CommunityListQueryParameterSerializerCyberstorm(data=request.query_params)
        qp.is_valid(raise_exception=True)

        params: OrderedDict = qp.validated_data
        communities_qs = self.get_queryset(params)
        communities_qs = self.order_queryset(
            params.get("ordering", "name"), communities_qs
        )
        serializer = self.paginate_and_serialize_results(communities_qs)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self, params=None) -> QuerySet[Community]:
        return Community.objects.listed().annotate(
            pkgs=Count(
                "package_listings",
                filter=Q(
                    Q(package_listings__package__is_deprecated=False)
                    & Q(
                        Case(
                            When(
                                require_package_listing_approval=True,
                                then=Case(
                                    When(
                                        Q(
                                            package_listings__review_status=PackageListingReviewStatus.approved
                                        ),
                                        then=True,
                                    ),
                                    default=False,
                                    output_field=BooleanField(),
                                ),
                            ),
                            default=Case(
                                When(
                                    Q(
                                        package_listings__review_status=PackageListingReviewStatus.unreviewed
                                    )
                                    | Q(
                                        package_listings__review_status=PackageListingReviewStatus.approved
                                    ),
                                    then=True,
                                ),
                                default=False,
                                output_field=BooleanField(),
                            ),
                        ),
                    ),
                ),
                distinct=True,
            ),
            downloads=Sum(
                Case(
                    When(package_listings__package__is_deprecated=True, then=0),
                    When(
                        package_listings__review_status=PackageListingReviewStatus.rejected,
                        then=0,
                    ),
                    default="package_listings__package__versions__downloads",
                )
            ),
        )

    def order_queryset(
        self, ordering: str, queryset: QuerySet[Community]
    ) -> QuerySet[Community]:
        order_arg = {
            "name": "name",
        }.get(ordering, "name")

        return queryset.order_by(Lower(order_arg))

    def paginate_and_serialize_results(
        self,
        communities_q: QuerySet[Community],
    ) -> CommunityListSerializerCyberstorm:
        page_q = self.paginate_queryset(communities_q)
        communities = [
            {
                "name": c.name,
                "identifier": c.identifier,
                "download_count": 0 if not c.downloads else c.downloads,
                "package_count": 0 if not c.pkgs else c.pkgs,
                "background_image_url": c.background_image_url,
                "description": c.description,
                "discord_link": c.discord_url,
            }
            for c in page_q
        ]

        return self.paginator.get_paginated_response(communities)
