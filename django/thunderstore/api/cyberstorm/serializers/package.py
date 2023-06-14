from rest_framework import serializers

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection
)
from thunderstore.repository.models import Namespace, Package, PackageVersion, Team


class PackageTeamMemberCyberstormSerializer(serializers.Serializer):
    user = serializers.CharField()
    imageSource = serializers.CharField(allow_null=True)
    role = serializers.CharField()

class PackageTeamCyberstormSerializer(serializers.Serializer):
    name = serializers.CharField()
    members = PackageTeamMemberCyberstormSerializer(many=True)

class PackageCategoryCyberstormSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageCategory
        fields = ["name", "slug"]


class PackageVersionCyberstormSerializer(serializers.Serializer):
    uploadDate = serializers.DateTimeField()
    downloadCount = serializers.IntegerField(min_value=0)
    version = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
    )
    changelog = serializers.CharField(
        max_length=PackageVersion._meta.get_field("changelog").max_length,
        allow_null=True,
        allow_blank=True
    )

class PackageCardCyberstormSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    shortDescription = serializers.CharField()
    imageSource = serializers.CharField(allow_null=True)
    downloadCount = serializers.IntegerField(min_value=0)
    likes = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField()
    author = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length
    )
    lastUpdated = serializers.DateTimeField()
    isPinned = serializers.BooleanField()
    isNsfw = serializers.BooleanField()
    isDeprecated = serializers.BooleanField()
    categories = PackageCategoryCyberstormSerializer(many=True)


class PackageDependencyCyberstormSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        allow_null=True,
        max_length=Community._meta.get_field("identifier").max_length,
    )
    # TODO: We need to either add a separate shortDescription or cut this off
    shortDescription = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    imageSource = serializers.CharField(allow_null=True)
    version = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
    )


class PackageDetailViewContentCyberstormSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=Package._meta.get_field("name").max_length
    )
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    shortDescription = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    imageSource = serializers.CharField(allow_null=True)
    downloadCount = serializers.IntegerField(min_value=0)
    likes = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField()
    author = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length
    )
    lastUpdated = serializers.DateTimeField()
    isPinned = serializers.BooleanField()
    isNsfw = serializers.BooleanField()
    isDeprecated = serializers.BooleanField()
    categories = PackageCategoryCyberstormSerializer(many=True)
    description = serializers.CharField()
    additionalImages = serializers.ListField(
        allow_empty=True,
        child=serializers.CharField()
    )
    gitHubLink = serializers.CharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length
    )
    donationLink = serializers.CharField()
    firstUploaded = serializers.DateTimeField()
    dependencyString = serializers.CharField(max_length=210)
    dependencies = PackageDependencyCyberstormSerializer(many=True)
    dependantCount = serializers.IntegerField(min_value=0)
    team = PackageTeamCyberstormSerializer()
    versions = PackageVersionCyberstormSerializer(many=True)

class PackageSearchQueryParameterCyberstormSerializer(serializers.Serializer):
    """
    For deserializing the query parameters used in package filtering.
    """

    page_size = serializers.IntegerField(default=20, min_value=1)
    community_identifier = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    package_identifier = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    team_identifier = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    user_identifier = serializers.CharField(allow_null=True, allow_blank=True, default=None)
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

class CommunityPackageListCyberstormSerializer(serializers.Serializer):
    """
    Data shown on Community's package list view on frontend.
    """

    categories = PackageCategoryCyberstormSerializer(many=True)
    packages = PackageCardCyberstormSerializer(many=True)
    pagesBehind = serializers.IntegerField()
    pagesAhead = serializers.IntegerField()
    pagesHasPrevious = serializers.BooleanField()
    pagesHasNext = serializers.BooleanField()