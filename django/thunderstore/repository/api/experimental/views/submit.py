from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import TemporaryUploadedFile
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers import (
    PackageSubmissionMetadataSerializer,
    PackageVersionSerializerExperimental,
)
from thunderstore.repository.package_upload import PackageUploadForm
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import download_file


class SubmitPackageApiView(APIView):
    """
    Submits a pre-uploaded package by upload uuid.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=PackageSubmissionMetadataSerializer(),
        responses={200: PackageVersionSerializerExperimental()},
        operation_id="experimental.package.submit",
    )
    def post(self, request):
        serializer = PackageSubmissionMetadataSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        file = self._download_file(serializer.validated_data["upload_uuid"])
        form = self._create_form(serializer.validated_data, file)
        if not form.is_valid():
            raise ValidationError(form.errors)
        package_version = form.save()
        serializer = PackageVersionSerializerExperimental(
            instance=package_version,
            context={"request": request},
        )
        return Response(serializer.data)

    def _download_file(self, upload_uuid: str) -> TemporaryUploadedFile:
        notfound = NotFound(
            "Upload not found or user has insufficient access permissions"
        )
        try:
            user_media = UserMedia.objects.get(uuid=upload_uuid)
        except ObjectDoesNotExist:
            raise notfound

        if not user_media.can_user_write(self.request.user):
            raise notfound

        client = get_s3_client()
        return download_file(self.request.user, client, user_media)

    def _create_form(self, data: Any, file: TemporaryUploadedFile) -> PackageUploadForm:
        return PackageUploadForm(
            user=self.request.user,
            community=self.request.community,
            data={
                "categories": data.get("categories"),
                "has_nsfw_content": data.get("has_nsfw_content"),
                "team": data.get("author_name"),
                "communities": data.get("communities"),
            },
            files={"file": file},
        )
