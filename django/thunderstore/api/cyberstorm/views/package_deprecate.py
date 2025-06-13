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


class SimpleSuccessResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="Success")


class DeprecatePackageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="cyberstorm.package.deprecate",
        request_body=DeprecatePackageSerializer,
        tags=["cyberstorm"],
        responses={status.HTTP_200_OK: SimpleSuccessResponseSerializer},
    )
    def post(self, request, namespace_id: str, package_name: str) -> Response:
        serializer = DeprecatePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = get_object_or_404(
            Package.objects.active(),
            namespace__name=namespace_id,
            name=package_name,
        )

        if serializer.validated_data["deprecate"]:
            deprecate_package(agent=request.user, package=package)
        else:
            undeprecate_package(agent=request.user, package=package)

        return Response({"message": "Success"}, status=status.HTTP_200_OK)
