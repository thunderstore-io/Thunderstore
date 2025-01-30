from rest_framework import serializers

from thunderstore.repository.models import PackageVersion
from thunderstore.repository.serializer_fields import ModelChoiceField


class ReportPackageListingRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
