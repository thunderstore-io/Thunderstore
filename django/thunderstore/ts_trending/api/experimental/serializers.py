from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from thunderstore.ts_trending.fields import ScoreField
from thunderstore.ts_trending.services.score import SORT_MODELS

SCHEMA_VERSION = 1


class IngestRequestSerializer(serializers.Serializer):
    schema_version = serializers.ChoiceField(choices=[SCHEMA_VERSION])
    computed_at = serializers.DateTimeField(
        label="When the query service computed the scores"
    )
    sorts = serializers.DictField(
        child=serializers.DictField(child=serializers.ListField(child=ScoreField())),
        label="Scores grouped by sort, then by community identifier",
    )

    def validate_computed_at(self, value: datetime) -> datetime:
        if value > timezone.now():
            raise serializers.ValidationError("Must not be in the future.")
        return value

    def validate_sorts(self, value: dict) -> dict:
        if set(value) != set(SORT_MODELS):
            raise serializers.ValidationError(
                f"Expected exactly these sorts: {', '.join(SORT_MODELS)}"
            )
        return value
