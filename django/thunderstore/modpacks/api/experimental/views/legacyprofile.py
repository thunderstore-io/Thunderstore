import logging
from datetime import datetime

from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from drf_yasg.openapi import TYPE_FILE, Schema
from drf_yasg.utils import swagger_auto_schema
from pydantic import BaseModel
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from thunderstore.core.utils import replace_cdn
from thunderstore.modpacks.models import LegacyProfile
from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message

logger = logging.getLogger(__name__)


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


class AnalyticsEventLegacyProfileExport(BaseModel):
    id: str
    timestamp: datetime
    file_size_bytes: int


def push_export_creation_to_kafka(key: str, file_size_bytes: int):
    try:
        send_kafka_message(
            topic=KafkaTopic.A_LEGACY_PROFILE_EXPORT_V1,
            payload_string=AnalyticsEventLegacyProfileExport(
                id=key,
                timestamp=timezone.now(),
                file_size_bytes=file_size_bytes,
            ).json(),
        )
    except Exception:
        logger.warning(
            "Failed to send legacy profile export event to Kafka", exc_info=True
        )


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
        key = LegacyProfile.objects.get_or_create_from_upload(
            content=self.request.data["file"]
        )
        serializer = LegacyProfileCreateResponseSerializer({"key": key})
        transaction.on_commit(
            lambda: push_export_creation_to_kafka(
                key=str(key), file_size_bytes=self.request.data["file"].size
            )
        )
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
        try:
            url = LegacyProfile.objects.get_file_url(key)
        except LegacyProfile.DoesNotExist:
            raise NotFound()

        url = self.request.build_absolute_uri(url)
        url = replace_cdn(url, request.query_params.get("cdn"))
        return redirect(url)
