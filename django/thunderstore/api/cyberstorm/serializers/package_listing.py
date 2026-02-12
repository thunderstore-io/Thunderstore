from rest_framework import serializers

from thunderstore.community.models import PackageCategory
from thunderstore.repository.api.experimental.serializers import (
    CommunityFilteredModelChoiceField,
)


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
