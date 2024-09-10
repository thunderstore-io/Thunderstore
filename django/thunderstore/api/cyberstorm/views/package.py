from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.forms import DeprecateForm
from thunderstore.repository.models import Package


class CyberstormDeprecatePackageRequestSerialiazer(serializers.Serializer):
    is_deprecated = serializers.BooleanField()


class CyberstormDeprecatePackageResponseSerialiazer(serializers.Serializer):
    is_deprecated = serializers.BooleanField()


class PackageDeprecateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormDeprecatePackageRequestSerialiazer,
        responses={200: CyberstormDeprecatePackageResponseSerialiazer},
        operation_id="cyberstorm.package.deprecate",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, namespace_id: str, package_name: str):
        serializer = CyberstormDeprecatePackageRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = get_object_or_404(
            Package,
            namespace__name=namespace_id,
            name__iexact=package_name,
        )
        form = DeprecateForm(
            user=request.user,
            instance=package,
            data=serializer.validated_data,
        )
        if form.is_valid():
            package = form.execute()
            return Response(CyberstormDeprecatePackageResponseSerialiazer(package).data)
        else:
            raise ValidationError(form.errors)
