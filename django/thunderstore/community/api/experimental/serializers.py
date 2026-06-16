from rest_framework import serializers

from thunderstore.community.models import PackageCategory
from thunderstore.repository.api.experimental.serializers import (
    CommunityFilteredModelChoiceField,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.ts_reports.consts import (
    REPORT_DESCRIPTION_MAX_LENGTH,
    REPORT_REASON_CHOICES_TUPLES,
)


class PackageListingUpdateRequestSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=CommunityFilteredModelChoiceField(
            queryset=PackageCategory.objects.all(),
            to_field="slug",
        ),
        allow_empty=True,
    )


class PackageCategoryExperimentalSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class PackageListingUpdateResponseSerializer(serializers.Serializer):
    categories = serializers.ListSerializer(
        child=PackageCategoryExperimentalSerializer()
    )


class PackageListingReportRequestSerializer(serializers.Serializer):
    # The reported version is identified by its SemVer version_number (what the
    # Cyberstorm API exposes), not a DB primary key. version_number is only
    # unique per package, so the lookup is scoped to the reported package passed
    # in via serializer context.
    version = serializers.SlugRelatedField(
        slug_field="version_number",
        required=False,
        allow_null=True,
        queryset=PackageVersion.objects.none(),
    )
    reason = serializers.ChoiceField(
        required=True,
        allow_blank=False,
        allow_null=False,
        choices=REPORT_REASON_CHOICES_TUPLES,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=REPORT_DESCRIPTION_MAX_LENGTH,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        package = self.context.get("package")
        if package is not None:
            self.fields["version"].queryset = package.versions.all()
