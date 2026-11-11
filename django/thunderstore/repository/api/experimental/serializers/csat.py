from datetime import datetime

from pydantic import BaseModel
from rest_framework import serializers


class CsatStatusResponseSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    eligible = serializers.BooleanField()


class CsatSubmitRequestSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    app_version = serializers.CharField(max_length=64)


class AnalyticsEventCsatSurveyResponse(BaseModel):
    id: str
    timestamp: datetime
    score: int
    comment: str
    app_version: str
