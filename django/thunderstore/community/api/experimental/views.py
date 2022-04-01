from collections import OrderedDict

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.api.experimental.serializers import CommunitySerializer
from thunderstore.community.models import Community
from thunderstore.frontend.api.experimental.serializers.views import (
    PackageCategorySerializer,
)


class CustomCursorPagination(CursorPagination):
    ordering = "-datetime_created"
    results_name = "results"
    page_size = 100

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    (
                        "pagination",
                        OrderedDict(
                            [
                                ("next_link", self.get_next_link()),
                                ("previous_link", self.get_previous_link()),
                            ],
                        ),
                    ),
                    (self.results_name, data),
                ],
            ),
        )


class CustomListAPIView(ListAPIView):
    pagination_class = CustomCursorPagination
    paginator: CustomCursorPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is None:
            raise ValueError("Pagination not set")

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CommunitiesExperimentalApiView(CustomListAPIView):
    pagination_class = CustomCursorPagination
    queryset = Community.objects.listed()
    serializer_class = CommunitySerializer


class PackageCategoriesExperimentalApiView(CustomListAPIView):
    pagination_class = CustomCursorPagination
    serializer_class = PackageCategorySerializer

    def get_queryset(self):
        community_identifier = self.kwargs.get("community")
        community = get_object_or_404(Community, identifier=community_identifier)
        return community.package_categories


class CurrentCommunityExperimentalApiView(APIView):
    serializer_class = CommunitySerializer

    @swagger_auto_schema(
        responses={200: serializer_class()},
        operation_id="experimental.community.current",
        operation_description="Fetch the Community of the queried domain",
    )
    def get(self, request, *args, **kwargs):
        serializer = CommunitySerializer(request.community)
        return Response(serializer.data, status=status.HTTP_200_OK)
