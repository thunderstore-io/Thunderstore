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


class CyberstormPackageListingReportRequestSerializer(serializers.Serializer):
    """
    Cyberstorm report request: identifies the reported version by its SemVer
    version_number (what the Cyberstorm API exposes), not a DB primary key.
    version_number is only unique per package, so the lookup is scoped to the
    reported package passed in via serializer context.

    The field is named `version_number` (not `version`) for forwards/backwards
    compatible deploys: the previously deployed serializer exposed a `version`
    field typed as a PK, which would reject this semver string with a 400. Using
    a new field name means an old backend simply ignores it (DRF drops unknown
    fields), so a frontend shipping this contract works before the backend does.

    The `Cyberstorm` class-name prefix keeps this distinct from the experimental
    API's PackageListingReportRequestSerializer: drf-yasg derives a schema
    ref_name from the class name and errors when two serializers share one.
    """

    version_number = serializers.SlugRelatedField(
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
            self.fields["version_number"].queryset = package.versions.all()


class PackageListingCategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class PackageListingCategoriesSerializer(serializers.Serializer):
    categories = PackageListingCategorySerializer(many=True)


class PackageListingUpdateSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=CommunityFilteredModelChoiceField(
            queryset=PackageCategory.objects.all(), to_field="slug"
        ),
        allow_empty=True,
    )


class PackageListingRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField()
    internal_notes = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )


class PackageListingApproveSerializer(serializers.Serializer):
    internal_notes = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )


class PackageListingStatusResponseSerializer(serializers.Serializer):
    review_status = serializers.CharField(required=False, allow_null=True)
    rejection_reason = serializers.CharField(required=False, allow_null=True)
    internal_notes = serializers.CharField(required=False, allow_null=True)
    listing_admin_url = serializers.CharField(required=False, allow_null=True)
    package_admin_url = serializers.CharField(required=False, allow_null=True)
