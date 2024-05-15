from rest_framework import serializers

from thunderstore.community.models import PackageCategory
from thunderstore.repository.api.experimental.serializers import (
    CommunityFilteredModelChoiceField,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.serializer_fields import ModelChoiceField
from thunderstore.ts_reports.models import PackageReportReason


class PackageListingUpdateRequestSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=CommunityFilteredModelChoiceField(
            queryset=PackageCategory.objects.all(),
            to_field="slug",
        ),
        allow_empty=True,
    )


class PackageListingReportRequestSerializer(serializers.Serializer):
    package_version_id = ModelChoiceField(
        PackageVersion.objects.all(), "pk", required=True
    )
    reason = ModelChoiceField(PackageReportReason.objects.active(), "pk", required=True)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class PackageCategoryExperimentalSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class PackageListingUpdateResponseSerializer(serializers.Serializer):
    categories = serializers.ListSerializer(
        child=PackageCategoryExperimentalSerializer()
    )
