from rest_framework import serializers

from thunderstore.community.models import PackageCategory
from thunderstore.repository.api.experimental.serializers import (
    CommunityFilteredModelChoiceField,
)


class PackageCategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class PackageListingUpdateSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=CommunityFilteredModelChoiceField(
            queryset=PackageCategory.objects.all(), to_field="slug"
        ),
        allow_empty=True,
    )

    def to_representation(self, instance):
        categories_data = [
            PackageCategorySerializer(instance=category).data
            for category in instance.categories.all()
        ]

        return {"categories": categories_data}


class PackageListingRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField()
    internal_notes = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )

    def to_representation(self, instance):
        return {}  # Empty response


class PackageListingApproveSerializer(serializers.Serializer):
    internal_notes = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )

    def to_representation(self, instance):
        return {}  # Empty response
