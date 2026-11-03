from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from rest_framework import serializers


class CsatSubmitRequestSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    install_id = serializers.UUIDField()
    app_version = serializers.CharField(max_length=64)


class AnalyticsEventCsatSurveyResponse(BaseModel):
    id: str
    timestamp: datetime
    score: int
    comment: str
    install_id: UUID
    app_version: str
