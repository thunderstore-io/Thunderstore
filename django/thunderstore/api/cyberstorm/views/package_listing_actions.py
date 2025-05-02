from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers.package_listing import (
    PackageListingApproveSerializer,
    PackageListingCategoriesSerializer,
    PackageListingRejectSerializer,
    PackageListingUpdateSerializer,
)
from thunderstore.api.cyberstorm.services.package_listing import (
    approve_package_listing,
    reject_package_listing,
    update_categories,
)
from thunderstore.repository.models import Community, PackageListing
from thunderstore.repository.views.package._utils import get_package_listing_or_404


def get_package_listing(
    namespace_id: str, package_name: str, community_id: str
) -> PackageListing:
    community = get_object_or_404(Community, identifier=community_id)
    return get_package_listing_or_404(
        namespace=namespace_id,
        name=package_name,
        community=community,
    )


class UpdatePackageListingCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageListingUpdateSerializer

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.update",
        request_body=serializer_class,
        responses={200: serializer_class},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing = get_package_listing(
            namespace_id=kwargs["namespace_id"],
            package_name=kwargs["package_name"],
            community_id=kwargs["community_id"],
        )

        ctx = {"community": listing.community}
        serializer = self.serializer_class(data=request.data, context=ctx)
        serializer.is_valid(raise_exception=True)

        categories = serializer.validated_data["categories"]
        update_categories(agent=request.user, categories=categories, listing=listing)

        response_serializer = PackageListingCategoriesSerializer(instance=listing)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class RejectPackageListingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageListingRejectSerializer

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.reject",
        request_body=serializer_class,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing = get_package_listing(
            namespace_id=kwargs["namespace_id"],
            package_name=kwargs["package_name"],
            community_id=kwargs["community_id"],
        )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        reject_package_listing(
            agent=request.user,
            reason=serializer.validated_data["rejection_reason"],
            notes=serializer.validated_data.get("internal_notes"),
            listing=listing,
        )

        return Response({"message": "Success"}, status=status.HTTP_200_OK)


class ApprovePackageListingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageListingApproveSerializer

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.approve",
        request_body=serializer_class,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing = get_package_listing(
            namespace_id=kwargs["namespace_id"],
            package_name=kwargs["package_name"],
            community_id=kwargs["community_id"],
        )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        approve_package_listing(
            agent=request.user,
            notes=serializer.validated_data.get("internal_notes"),
            listing=listing,
        )

        return Response({"message": "Success"}, status=status.HTTP_200_OK)
