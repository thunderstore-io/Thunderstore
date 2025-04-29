from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package import (
    deprecate_package,
    undeprecate_package,
)
from thunderstore.repository.models import Package


class DeprecatePackageSerializer(serializers.Serializer):
    deprecate = serializers.BooleanField(required=True)


class DeprecatePackageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_package(self, namespace_name: str, package_name: str) -> Package:
        package = get_object_or_404(
            Package.objects.active(),
            namespace__name=namespace_name,
            name=package_name,
        )
        return package

    @swagger_auto_schema(
        operation_id="cyberstorm.package.deprecate",
        request_body=DeprecatePackageSerializer,
        tags=["cyberstorm"],
    )
    def post(self, request, namespace_id: str, package_name: str) -> Response:
        serializer = DeprecatePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        should_deprecate = serializer.validated_data["deprecate"]
        package = self.get_package(namespace_id, package_name)

        if should_deprecate:
            deprecate_package(package, request.user)
        else:
            undeprecate_package(package, request.user)

        return Response(status=status.HTTP_200_OK)
