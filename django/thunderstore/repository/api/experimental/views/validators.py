from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers.validators import (
    IconValidatorParamsSerializer,
    ManifestV1ValidatorParamsSerializer,
    ReadmeValidatorParamsSerializer,
    ValidatorResponseSerializer,
)
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.repository.validation.icon import validate_icon
from thunderstore.repository.validation.manifest import validate_manifest
from thunderstore.repository.validation.markdown import validate_markdown


class ReadmeValidatorApiView(APIView):
    """
    Validates a package readme.
    """

    permission_classes = [permissions.IsAuthenticated]
    params_serializer_class = ReadmeValidatorParamsSerializer
    response_serializer_class = ValidatorResponseSerializer

    @swagger_auto_schema(
        request_body=params_serializer_class(),
        responses={200: response_serializer_class()},
        operation_id="experimental.submission.validate.readme",
    )
    def post(self, request):
        serializer = self.params_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        validate_markdown(serializer.validated_data["readme_data"])

        return Response(
            self.response_serializer_class(
                instance={"success": True},
                context={"request": request},
            ).data
        )


class ManifestV1ValidatorApiView(APIView):
    """
    Validates a package manifest.
    """

    permission_classes = [permissions.IsAuthenticated]
    params_serializer_class = ManifestV1ValidatorParamsSerializer
    response_serializer_class = ValidatorResponseSerializer

    @swagger_auto_schema(
        request_body=params_serializer_class(),
        responses={200: response_serializer_class()},
        operation_id="experimental.submission.validate.manifest-v1",
    )
    def post(self, request):
        serializer = self.params_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        validate_manifest(
            format_spec=PackageFormats.get_active_format(),
            user=request.user,
            team=serializer.validated_data["namespace"],
            manifest_data=serializer.validated_data["manifest_data"],
        )

        return Response(
            self.response_serializer_class(
                instance={"success": True},
                context={"request": request},
            ).data
        )


class IconValidatorApiView(APIView):
    """
    Validates a package icon.
    """

    permission_classes = [permissions.IsAuthenticated]
    params_serializer_class = IconValidatorParamsSerializer
    response_serializer_class = ValidatorResponseSerializer

    @swagger_auto_schema(
        request_body=params_serializer_class(),
        responses={200: response_serializer_class()},
        operation_id="experimental.submission.validate.icon",
    )
    def post(self, request):
        serializer = self.params_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validate_icon(serializer.validated_data["icon_data"])
        return Response(
            self.response_serializer_class(
                instance={"success": True},
                context={"request": request},
            ).data
        )
