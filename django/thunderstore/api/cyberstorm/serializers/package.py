from rest_framework import serializers

from . import CyberstormCommunitySerializer
from .team import CyberstormTeamSerializer


class CyberstormPackageCategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class CyberstormPackageVersionMinimalSerializer(serializers.Serializer):
    identifier = serializers.CharField(source="full_version_name")
    namespace = serializers.CharField()
    name = serializers.CharField()
    version_number = serializers.CharField()
    description = serializers.CharField()

    datetime_created = serializers.DateTimeField(source="date_created")
    file_size = serializers.IntegerField()
    icon_url = serializers.CharField()

    download_count = serializers.IntegerField(source="downloads")


class CyberstormPackageSerializer(serializers.Serializer):
    name = serializers.CharField()
    namespace = serializers.CharField()

    display_name = serializers.CharField()
    description = serializers.CharField()

    icon_url = serializers.CharField()

    download_count = serializers.IntegerField(source="downloads")
    rating_score = serializers.IntegerField()
    file_size = serializers.IntegerField()

    datetime_created = serializers.DateTimeField(source="date_created")
    datetime_updated = serializers.DateTimeField(source="date_updated")
    is_pinned = serializers.BooleanField()
    is_deprecated = serializers.BooleanField()

    website_url = serializers.CharField()
    dependant_count = serializers.IntegerField(min_value=0)
    owner = CyberstormTeamSerializer()

    dependencies_count = serializers.IntegerField()
    dependencies_preview = CyberstormPackageVersionMinimalSerializer(many=True)
    versions_count = serializers.IntegerField()
    versions_preview = CyberstormPackageVersionMinimalSerializer(many=True)


class CyberstormPackageListingMetaSerializer(serializers.Serializer):
    community = CyberstormCommunitySerializer()
    package = CyberstormPackageSerializer()
    categories = CyberstormPackageCategorySerializer(many=True)
    review_status = serializers.CharField()

    has_nsfw_content = serializers.BooleanField()
