from collections import OrderedDict
from typing import List, Set

from django.db.models import QuerySet
from drf_yasg.openapi import IN_QUERY, TYPE_ARRAY, TYPE_STRING, Items, Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from thunderstore.community.api.experimental.serializers import (
    PackageValidationResponseSerializer,
)
from thunderstore.community.models import Community
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.frontend.api.experimental.serializers.views import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.repository.package_reference import PackageReference


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


class PackageValidationExperimentalApiView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                "mods",
                IN_QUERY,
                "Canonical package names including version numbers",
                type=TYPE_ARRAY,
                items=Items(type=TYPE_STRING),
            ),
        ],
        responses={
            200: PackageValidationResponseSerializer(),
            400: "Unknown community_id in path",
        },
        operation_id="experimental.community.validate-packages",
        operation_description="Validate list of packages exist in a community",
    )
    def get(self, request: Request, community_id: str):
        try:
            community = Community.objects.listed().get(identifier=community_id)
        except Community.DoesNotExist:
            return Response(f'Unknown community "{community_id}"', HTTP_400_BAD_REQUEST)

        submitted_mods = [m.strip() for m in request.GET.getlist("mods")]
        errors: List[str] = []

        if not submitted_mods:
            return Response({"validation_errors": errors})

        listings: QuerySet[PackageListing] = (
            community.package_listings.active()
            .annotate_canonical_name()
            .only("id")  # We're only interested in the annotated field.
        )
        valid_mods: Set[str] = set(l.canonical_name for l in listings)

        for mod in submitted_mods:
            try:
                ref = PackageReference.parse(mod)
            except ValueError as e:
                errors.append(str(e))
                continue

            if ref.version is None:
                errors.append(f"Missing version number: {mod}")
            elif mod not in valid_mods:
                errors.append(f"Package {mod} is not listed in {community_id}")

        return Response({"validation_errors": errors})


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
