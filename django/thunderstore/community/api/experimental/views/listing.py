from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response

from thunderstore.api.cyberstorm.services.package_listing import (
    approve_package_listing,
    reject_package_listing,
    report_package_listing,
    update_categories,
)
from thunderstore.community.api.experimental.serializers import (
    PackageListingUpdateRequestSerializer,
    PackageListingUpdateResponseSerializer,
)
from thunderstore.community.models import PackageListing
from thunderstore.repository.models import PackageVersion


class PackageListingUpdateApiView(GenericAPIView):
    queryset = PackageListing.objects.active().select_related(
        "community",
        "package",
    )
    serializer_class = PackageListingUpdateResponseSerializer

    @swagger_auto_schema(
        operation_id="experimental.package_listing.update",
        request_body=PackageListingUpdateRequestSerializer,
        responses={200: serializer_class()},
        tags=["experimental"],
    )
    def post(self, request, *args, **kwargs):
        listing: PackageListing = self.get_object()

        request_serializer = PackageListingUpdateRequestSerializer(
            data=request.data, context={"community": listing.community}
        )
        request_serializer.is_valid(raise_exception=True)

        update_categories(
            agent=request.user,
            categories=request_serializer.validated_data["categories"],
            listing=listing,
        )

        serializer = self.serializer_class(instance=listing)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PackageListingRejectRequestSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField()
    internal_notes = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )


class PackageListingRejectApiView(GenericAPIView):
    queryset = PackageListing.objects.select_related("community", "package")

    @swagger_auto_schema(
        operation_id="experimental.package_listing.reject",
        request_body=PackageListingRejectRequestSerializer,
        tags=["experimental"],
    )
    def post(self, request, *args, **kwargs):
        listing: PackageListing = self.get_object()

        request_serializer = PackageListingRejectRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        reject_package_listing(
            agent=request.user,
            reason=request_serializer.validated_data["rejection_reason"],
            notes=request_serializer.validated_data.get("internal_notes"),
            listing=listing,
        )

        return Response(status=status.HTTP_200_OK)


class PackageListingApproveRequestSerializer(serializers.Serializer):
    internal_notes = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )


class PackageListingApproveApiView(GenericAPIView):
    queryset = PackageListing.objects.select_related("community", "package")

    @swagger_auto_schema(
        operation_id="experimental.package_listing.approve",
        tags=["experimental"],
        request_body=PackageListingApproveRequestSerializer,
        responses={200: "Success"},
    )
    def post(self, request, *args, **kwargs):
        listing: PackageListing = self.get_object()

        request_serializer = PackageListingApproveRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        approve_package_listing(
            agent=request.user,
            notes=request_serializer.validated_data.get("internal_notes"),
            listing=listing,
        )

        return Response(status=status.HTTP_200_OK)


class PackageListingReportRequestSerializer(serializers.Serializer):
    version = PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        queryset=PackageVersion.objects.all(),
    )
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class PackageListingReportApiView(GenericAPIView):
    queryset = PackageListing.objects.select_related("package")
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="experimental.package_listing.report",
        tags=["experimental"],
        request_body=PackageListingReportRequestSerializer,
        responses={200: "Success"},
    )
    def post(self, request, *args, **kwargs):
        listing: PackageListing = self.get_object()

        request_serializer = PackageListingReportRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        report_package_listing(
            agent=request.user,
            reason=request_serializer.validated_data.get("reason"),
            package=listing.package,
            package_listing=listing,
            package_version=request_serializer.validated_data.get("version"),
            description=request_serializer.validated_data.get("description"),
        )

        return Response(status=status.HTTP_200_OK)
