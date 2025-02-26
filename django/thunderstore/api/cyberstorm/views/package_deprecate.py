from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.models import Namespace, Package


class DeprecatePackageSerializer(serializers.Serializer):
    deprecate = serializers.BooleanField(required=True)


class DeprecatePackageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, namespace_id: str, package_name: str) -> Package:
        namespace = get_object_or_404(Namespace, name=namespace_id)
        package = get_object_or_404(Package, name=package_name, namespace=namespace)
        return package

    @conditional_swagger_auto_schema(
        request_body=DeprecatePackageSerializer,
        responses={200: "Success"},
        operation_id="cyberstorm.package.deprecate",
        tags=["cyberstorm"],
    )
    def post(self, request, namespace_id: str, package_name: str) -> Response:
        package = self.get_object(namespace_id, package_name)

        if not package.can_user_manage_deprecation(self.request.user):
            raise PermissionDenied()

        serializer = DeprecatePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        should_deprecate = serializer.validated_data["deprecate"]
        package.deprecate() if should_deprecate else package.undeprecate()

        return Response({"message": "Success"}, status=status.HTTP_200_OK)
