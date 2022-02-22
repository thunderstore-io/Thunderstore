from rest_framework import serializers

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.repository.models import Package, PackageVersion, Team


class CommunityCardSerializer(serializers.Serializer):
    """
    Data shown on "CommunityCard" component on frontend.
    """

    download_count = serializers.IntegerField(min_value=0)
    bg_image_src = serializers.CharField(allow_null=True)
    identifier = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    package_count = serializers.IntegerField(min_value=0)
    name = serializers.CharField(
        max_length=Community._meta.get_field("name").max_length
    )


class PackageCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageCategory
        fields = ["name", "slug"]


class PackageCardSerializer(serializers.Serializer):
    """
    Data shown on "PackageCard" component on frontend.
    """

    categories = PackageCategorySerializer(many=True)
    community_identifier = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    community_name = serializers.CharField(
        max_length=Community._meta.get_field("name").max_length
    )
    description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    download_count = serializers.IntegerField(min_value=0)
    image_src = serializers.CharField(allow_null=True)
    is_deprecated = serializers.BooleanField()
    is_nsfw = serializers.BooleanField()
    is_pinned = serializers.BooleanField()
    last_updated = serializers.DateTimeField()
    package_name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    rating_score = serializers.IntegerField(min_value=0)
    team_name = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length
    )


class CommunityPackageListSerializer(serializers.Serializer):
    """
    Data shown on Community's package list view on frontend.
    """

    bg_image_src = serializers.CharField(allow_null=True)
    categories = PackageCategorySerializer(many=True)
    community_name = serializers.CharField(
        max_length=Community._meta.get_field("name").max_length
    )
    packages = PackageCardSerializer(many=True)


class FrontPageContentSerializer(serializers.Serializer):
    """
    Front page contains general and community specific stats.
    """

    communities = CommunityCardSerializer(many=True)
    download_count = serializers.IntegerField(min_value=0)
    package_count = serializers.IntegerField(min_value=0)


class PackageSearchQueryParameterSerializer(serializers.Serializer):
    """
    For deserializing the query parameters used in package filtering.
    """

    deprecated = serializers.BooleanField(default=False)
    excluded_categories = serializers.ListField(
        child=serializers.SlugField(), default=[]
    )
    included_categories = serializers.ListField(
        child=serializers.SlugField(), default=[]
    )
    nsfw = serializers.BooleanField(default=False)
    ordering = serializers.CharField(default="last-updated")
    page = serializers.IntegerField(default=1, min_value=1)
    q = serializers.CharField(required=False)
    section = serializers.CharField(
        max_length=PackageListingSection._meta.get_field("name").max_length,
        required=False,
    )
