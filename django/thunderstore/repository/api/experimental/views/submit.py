from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import TemporaryUploadedFile
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers import (
    PackageSubmissionMetadataSerializer,
    PackageSubmissionResult,
)
from thunderstore.repository.package_upload import PackageUploadForm
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import download_file


def get_usermedia_or_404(user, usermedia_uuid: str) -> UserMedia:
    notfound = NotFound("Upload not found or user has insufficient access permissions")
    try:
        user_media = UserMedia.objects.get(uuid=usermedia_uuid)
    except ObjectDoesNotExist:
        raise notfound

    if not user_media.can_user_write(user):
        raise notfound

    return user_media


class SubmitPackageApiView(APIView):
    """
    Submits a pre-uploaded package by upload uuid.
    """

    @swagger_auto_schema(
        request_body=PackageSubmissionMetadataSerializer(),
        responses={200: PackageSubmissionResult()},
        operation_id="experimental.package.submit",
        tags=["experimental"],
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

        listings = package_version.package.community_listings.active()
        available_communities = []
        for listing in listings:
            available_communities.append(
                {
                    "community": listing.community,
                    "categories": listing.categories.all(),
                    "url": listing.get_full_url(),
                }
            )

        serializer = PackageSubmissionResult(
            instance={
                "package_version": package_version,
                "available_communities": available_communities,
            },
            context={"request": request},
        )
        return Response(serializer.data)

    def _download_file(self, upload_uuid: str) -> TemporaryUploadedFile:
        user_media = get_usermedia_or_404(self.request.user, upload_uuid)
        client = get_s3_client()
        return download_file(self.request.user, client, user_media)

    def _create_form(self, data: Any, file: TemporaryUploadedFile) -> PackageUploadForm:
        return PackageUploadForm(
            user=self.request.user,
            community=self.request.community,
            data={
                "categories": data.get("categories", []),
                "community_categories": data.get("community_categories", {}),
                "has_nsfw_content": data.get("has_nsfw_content"),
                "team": data.get("author_name"),
                "communities": data.get("communities"),
            },
            files={"file": file},
        )
