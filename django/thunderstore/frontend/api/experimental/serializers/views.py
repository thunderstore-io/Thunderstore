from rest_framework import serializers

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.repository.models import Namespace, Package, PackageVersion, Team


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = (
            "identifier",
            "name",
            "discord_url",
            "wiki_url",
            "require_package_listing_approval",
        )


class CommunityCardSerializer(serializers.Serializer):
    """
    Data shown on "CommunityCard" component on frontend.
    """

    bg_image_src = serializers.CharField(allow_null=True)
    download_count = serializers.IntegerField(min_value=0)
    identifier = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    name = serializers.CharField(
        max_length=Community._meta.get_field("name").max_length
    )
    package_count = serializers.IntegerField(min_value=0)


class PackageCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageCategory
        fields = ["name", "slug"]


class PackageVersionSerializer(serializers.Serializer):
    """
    Data shown on "PackageVersions" component on frontend.
    """

    date_created = serializers.DateTimeField()
    download_count = serializers.IntegerField(min_value=0)
    download_url = serializers.CharField()
    install_url = serializers.CharField()
    version_number = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
    )


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
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    package_name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    rating_score = serializers.IntegerField(min_value=0)
    team_name = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length
    )


class PackageDependencySerializer(serializers.Serializer):
    """
    Data shown on "PackageRequirements" component on frontend.
    """

    community_identifier = serializers.CharField(
        allow_null=True,
        max_length=Community._meta.get_field("identifier").max_length,
    )
    community_name = serializers.CharField(
        allow_null=True,
        max_length=Community._meta.get_field("name").max_length,
    )
    description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    image_src = serializers.CharField(allow_null=True)
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    package_name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    version_number = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
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
    has_more_pages = serializers.BooleanField()
    packages = PackageCardSerializer(many=True)


class FrontPageContentSerializer(serializers.Serializer):
    """
    Front page contains general and community specific stats.
    """

    communities = CommunityCardSerializer(many=True)
    download_count = serializers.IntegerField(min_value=0)
    package_count = serializers.IntegerField(min_value=0)


class PackageDetailViewContentSerializer(serializers.Serializer):
    """
    Data shown on Package's detail view on frontend.
    """

    bg_image_src = serializers.CharField(allow_null=True)
    categories = PackageCategorySerializer(many=True)
    community_identifier = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    community_name = serializers.CharField(
        max_length=Community._meta.get_field("name").max_length
    )
    dependant_count = serializers.IntegerField(min_value=0)
    dependencies = PackageDependencySerializer(many=True)
    dependency_string = serializers.CharField(max_length=210)
    description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    download_count = serializers.IntegerField(min_value=0)
    download_url = serializers.CharField()
    image_src = serializers.CharField(allow_null=True)
    install_url = serializers.CharField()
    last_updated = serializers.DateTimeField()
    markdown = serializers.CharField()
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    package_name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    rating_score = serializers.IntegerField(min_value=0)
    team_name = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length
    )
    versions = PackageVersionSerializer(many=True)
    website = serializers.CharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length
    )


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
