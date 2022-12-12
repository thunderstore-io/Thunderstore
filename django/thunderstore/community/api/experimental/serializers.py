from rest_framework import serializers

from thunderstore.community.models import PackageCategory
from thunderstore.repository.api.experimental.serializers import (
    CommunityFilteredModelChoiceField,
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
