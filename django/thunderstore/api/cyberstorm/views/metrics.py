from django.http import HttpRequest
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers.metrics import (
    PackageDownloadMetricsResponseSerializer,
    PackageVersionDownloadMetricsResponseSerializer,
)
from thunderstore.api.cyberstorm.services.metrics import (
    get_package_download_metrics,
    get_package_version_download_metrics,
)
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.repository.models import Package, PackageVersion


class DownloadMetricsQueryParamsSerializer(serializers.Serializer):
    """
    Query parameters for download metrics endpoints.
    """

    days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        required=False,
        help_text="Number of days of historical data to return (1-365)",
    )


class PackageVersionDownloadMetricsAPIView(CyberstormAutoSchemaMixin, APIView):
    """
    Get historical download metrics for a specific package version.
    """

    @conditional_swagger_auto_schema(
        query_serializer=DownloadMetricsQueryParamsSerializer,
        responses={200: PackageVersionDownloadMetricsResponseSerializer},
        operation_id="cyberstorm.package_version.download_metrics",
        tags=["cyberstorm"],
    )
    def get(
        self,
        request: HttpRequest,
        namespace_id: str,
        package_name: str,
        version_number: str,
    ) -> Response:
        version = get_object_or_404(
            PackageVersion.objects.filter(is_active=True).select_related(
                "package",
                "package__namespace",
            ),
            package__namespace__name=namespace_id,
            name=package_name,
            version_number=version_number,
        )

        query_params = DownloadMetricsQueryParamsSerializer(data=request.query_params)
        query_params.is_valid(raise_exception=True)
        days = query_params.validated_data["days"]

        response_data = get_package_version_download_metrics(version, days)

        response_serializer = PackageVersionDownloadMetricsResponseSerializer(
            data=response_data
        )
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PackageDownloadMetricsAPIView(CyberstormAutoSchemaMixin, APIView):
    """
    Get aggregated historical download metrics for all versions of a package.
    """

    @conditional_swagger_auto_schema(
        query_serializer=DownloadMetricsQueryParamsSerializer,
        responses={200: PackageDownloadMetricsResponseSerializer},
        operation_id="cyberstorm.package.download_metrics",
        tags=["cyberstorm"],
    )
    def get(
        self,
        request: HttpRequest,
        namespace_id: str,
        package_name: str,
    ) -> Response:
        package = get_object_or_404(
            Package.objects.filter(is_active=True).select_related("namespace"),
            namespace__name=namespace_id,
            name=package_name,
        )

        query_params = DownloadMetricsQueryParamsSerializer(data=request.query_params)
        query_params.is_valid(raise_exception=True)
        days = query_params.validated_data["days"]

        response_data = get_package_download_metrics(package, days)

        response_serializer = PackageDownloadMetricsResponseSerializer(
            data=response_data
        )
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

