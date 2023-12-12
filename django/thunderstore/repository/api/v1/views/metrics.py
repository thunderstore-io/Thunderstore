from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.models import Package, PackageVersion


class PackageMetricsSerializer(serializers.Serializer):
    downloads = serializers.IntegerField()
    rating_score = serializers.IntegerField()


# This view is potentialy used by the shields.io project and should be kept
# backwards-compatible
class PackageMetricsApiView(APIView):
    @swagger_auto_schema(
        operation_id="api_v1_package_metrics",
        responses={200: PackageMetricsSerializer()},
        tags=["v1"],
    )
    def get(self, request: Request, namespace: str, name: str):
        obj = get_object_or_404(
            Package.objects.active(),
            namespace__name=namespace,
            name=name,
        )
        return Response(PackageMetricsSerializer(obj).data)


class PackageVersionMetricsSerializer(serializers.Serializer):
    downloads = serializers.IntegerField()


# This view is potentialy used by the shields.io project and should be kept
# backwards-compatible
class PackageVersionMetricsApiView(APIView):
    @swagger_auto_schema(
        operation_id="api_v1_package_version_metrics",
        responses={200: PackageVersionMetricsSerializer()},
        tags=["v1"],
    )
    def get(self, request: Request, namespace: str, name: str, version: str):
        obj = get_object_or_404(
            PackageVersion.objects.active(),
            package__is_active=True,
            package__namespace__name=namespace,
            name=name,
            version_number=version,
        )
        return Response(PackageVersionMetricsSerializer(obj).data)
