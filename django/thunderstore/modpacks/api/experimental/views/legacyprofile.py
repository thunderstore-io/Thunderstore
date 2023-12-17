from django.shortcuts import redirect
from django.utils import timezone
from drf_yasg.openapi import TYPE_FILE, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from thunderstore.core.utils import replace_cdn
from thunderstore.modpacks.models import LegacyProfile


class LegacyProfileCreateResponseSerializer(serializers.Serializer):
    key = serializers.CharField(required=True)


# We need to override the get_filename function since DRF for some reason
# explicitly requires a filename, which we don't really care about
class LegacyProfileFileUploadParser(FileUploadParser):
    def get_filename(self, stream, media_type, parser_context):
        return f"upload-{timezone.now().timestamp()}.bin"


class LegacyProfileCreateThrottle(UserRateThrottle):
    def get_rate(self) -> str:
        return "6/m"


class LegacyProfileCreateApiView(APIView):
    permission_classes = []
    parser_classes = [LegacyProfileFileUploadParser]
    throttle_classes = [LegacyProfileCreateThrottle]

    @swagger_auto_schema(
        request_body=Schema(title="content", type=TYPE_FILE),
        responses={200: LegacyProfileCreateResponseSerializer()},
        operation_id="experimental.modpacks.legacyprofile.create",
        tags=["experimental"],
    )
    def post(self, request, *args, **kwargs):
        if "file" not in self.request.data or not self.request.data["file"]:
            raise ValidationError(detail="Request body was empty")
        profile = LegacyProfile.objects.get_or_create_from_upload(
            content=self.request.data["file"]
        )
        serializer = LegacyProfileCreateResponseSerializer({"key": profile.id})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class LegacyProfileRetrieveApiView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: Schema(title="content", type=TYPE_FILE)},
        operation_id="experimental.modpacks.legacyprofile.retrieve",
        tags=["experimental"],
    )
    def get(self, request, key: str, *args, **kwargs):
        profile = get_object_or_404(LegacyProfile, id=key)
        url = self.request.build_absolute_uri(profile.file.url)
        url = replace_cdn(url, request.query_params.get("cdn"))
        return redirect(url)
