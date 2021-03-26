from collections import OrderedDict

from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from thunderstore.community.api.experimental.serializers import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.community.models import Community


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


class CommunitiesPagination(CustomCursorPagination):
    results_name = "communities"


class CommunitiesExperimentalApiView(CustomListAPIView):
    pagination_class = CommunitiesPagination
    queryset = Community.objects.listed()
    serializer_class = CommunitySerializer


class PackageCategoriesPagination(CustomCursorPagination):
    results_name = "package_categories"


class PackageCategoriesExperimentalApiView(CustomListAPIView):
    pagination_class = PackageCategoriesPagination
    serializer_class = PackageCategorySerializer

    def get_queryset(self):
        community_identifier = self.kwargs.get("community")
        community = get_object_or_404(Community, identifier=community_identifier)
        return community.package_categories
