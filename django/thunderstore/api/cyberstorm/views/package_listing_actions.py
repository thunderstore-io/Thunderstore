from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers.package_listing import (
    PackageListingApproveSerializer,
    PackageListingRejectSerializer,
    PackageListingUpdateSerializer,
)
from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.views.package._utils import get_package_listing_or_404


class BasePackageListingActionView(GenericAPIView):
    def get_community(self) -> Community:
        community_id = self.kwargs.get("community_id")
        community = get_object_or_404(Community, identifier=community_id)
        return community

    def get_object(self) -> PackageListing:
        return get_package_listing_or_404(
            namespace=self.kwargs["namespace_id"],
            name=self.kwargs["package_name"],
            community=self.get_community(),
        )

    def clear_package_listing_cache_with_args(self, listing: PackageListing) -> None:
        get_package_listing_or_404.clear_cache_with_args(
            namespace=listing.package.namespace.name,
            name=listing.package.name,
            community=listing.community,
        )

    def validate_serializer_and_get_params(self, data: dict) -> dict:
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class UpdatePackageListingCategoriesAPIView(BasePackageListingActionView):
    queryset = PackageListing.objects.active().select_related(
        "community",
        "package",
    )
    serializer_class = PackageListingUpdateSerializer

    def _update_categories(self, listing: PackageListing, categories: list) -> None:
        listing.update_categories(
            agent=self.request.user,
            categories=categories,
        )
        self.clear_package_listing_cache_with_args(listing)

    def get_object(self) -> PackageListing:
        listing = super().get_object()
        if not listing.check_update_categories_permission(self.request.user):
            raise PermissionDenied()
        return listing

    def validate_data(
        self, data: dict, listing: PackageListing
    ) -> PackageListingUpdateSerializer:
        ctx = {"community": listing.community}
        serializer = self.serializer_class(data=data, context=ctx)
        serializer.is_valid(raise_exception=True)
        return serializer

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.update",
        request_body=PackageListingUpdateSerializer,
        responses={200: serializer_class()},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing: PackageListing = self.get_object()
        serializer = self.validate_data(request.data, listing)
        categories = serializer.validated_data["categories"]

        self._update_categories(listing, categories)

        serializer = self.serializer_class(instance=listing)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RejectPackageListingAPIView(BasePackageListingActionView):
    queryset = PackageListing.objects.select_related("community", "package")
    serializer_class = PackageListingRejectSerializer

    def _reject(self, listing: PackageListing, params: dict) -> None:
        reason = params["rejection_reason"]
        notes = params.get("internal_notes")

        listing.reject(
            agent=self.request.user, rejection_reason=reason, internal_notes=notes
        )
        listing.clear_review_request()
        self.clear_package_listing_cache_with_args(listing)

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.reject",
        request_body=PackageListingRejectSerializer,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing: PackageListing = self.get_object()
        params = self.validate_serializer_and_get_params(request.data)

        try:
            self._reject(listing, params)
            return Response({"message": "Success"}, status=200)
        except PermissionError:
            raise PermissionDenied()


class ApprovePackageListingAPIView(BasePackageListingActionView):
    queryset = PackageListing.objects.select_related("community", "package")
    serializer_class = PackageListingApproveSerializer

    def _approve(self, listing: PackageListing, params: dict) -> None:
        notes = params.get("internal_notes")
        listing.approve(agent=self.request.user, internal_notes=notes)
        listing.clear_review_request()
        self.clear_package_listing_cache_with_args(listing)

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.approve",
        request_body=PackageListingApproveSerializer,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing: PackageListing = self.get_object()
        params = self.validate_serializer_and_get_params(request.data)

        try:
            self._approve(listing, params)
            return Response({"message": "Success"}, status=200)
        except PermissionError:
            raise PermissionDenied()
