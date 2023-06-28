from rest_framework import serializers

from thunderstore.community.models import Community, PackageCategory
from thunderstore.repository.models import Namespace, Package, PackageVersion, Team


class PackageTeamMemberSerializerCyberstorm(serializers.Serializer):
    user = serializers.CharField()
    image_source = serializers.CharField(allow_null=True)
    role = serializers.CharField()


class PackageTeamSerializerCyberstorm(serializers.Serializer):
    name = serializers.CharField()
    members = PackageTeamMemberSerializerCyberstorm(many=True)


class PackageCategorySerializerCyberstorm(serializers.ModelSerializer):
    class Meta:
        model = PackageCategory
        fields = ["name", "slug"]


class PackageVersionSerializerCyberstorm(serializers.Serializer):
    upload_date = serializers.DateTimeField()
    download_count = serializers.IntegerField(min_value=0)
    version = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
    )
    changelog = serializers.CharField(
        max_length=PackageVersion._meta.get_field("changelog").max_length,
        allow_null=True,
        allow_blank=True,
    )


class PackageSerializerCyberstorm(serializers.Serializer):
    name = serializers.CharField(max_length=Package._meta.get_field("name").max_length)
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    short_description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    image_source = serializers.CharField(allow_null=True)
    download_count = serializers.IntegerField(min_value=0)
    likes = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField()
    author = serializers.CharField(max_length=Team._meta.get_field("name").max_length)
    last_updated = serializers.DateTimeField()
    is_pinned = serializers.BooleanField()
    is_nsfw = serializers.BooleanField()
    is_deprecated = serializers.BooleanField()
    categories = PackageCategorySerializerCyberstorm(many=True)


class PackageDependencySerializerCyberstorm(serializers.Serializer):
    name = serializers.CharField(max_length=Package._meta.get_field("name").max_length)
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        allow_null=True,
        max_length=Community._meta.get_field("identifier").max_length,
    )
    short_description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    image_source = serializers.CharField(allow_null=True)
    version = serializers.CharField(
        max_length=PackageVersion._meta.get_field("version_number").max_length
    )


class PackageDetailSerializerCyberstorm(PackageSerializerCyberstorm):
    description = serializers.CharField()
    github_link = serializers.CharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length
    )
    donation_link = serializers.CharField()
    first_uploaded = serializers.DateTimeField()
    dependency_string = serializers.CharField(max_length=210)
    dependencies = PackageDependencySerializerCyberstorm(many=True)
    dependant_count = serializers.IntegerField(min_value=0)
    team = PackageTeamSerializerCyberstorm()
    versions = PackageVersionSerializerCyberstorm(many=True)


class PackageListSearchQueryParameterSerializerCyberstorm(serializers.Serializer):
    page_size = serializers.IntegerField(default=20, min_value=1)
    community_id = serializers.CharField(
        allow_null=True, allow_blank=True, default=None
    )
    namespace = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    package_id = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    team_id = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    user_id = serializers.CharField(allow_null=True, allow_blank=True, default=None)
    include_deprecated = serializers.BooleanField(default=False)
    excluded_categories = serializers.ListField(
        child=serializers.SlugField(), default=[]
    )
    included_categories = serializers.ListField(
        child=serializers.SlugField(), default=[]
    )
    include_nsfw = serializers.BooleanField(default=False)
    ordering = serializers.ChoiceField(
        required=False,
        choices=["last-updated", "most-downloaded", "newest", "top-rated"],
    )
    page = serializers.IntegerField(default=1, min_value=1)
    q = serializers.CharField(required=False)
    section = serializers.CharField(
        required=False,
    )


class PackageListSerializerCyberstorm(serializers.Serializer):
    current = serializers.IntegerField()
    final = serializers.IntegerField()
    total = serializers.IntegerField()
    count = serializers.IntegerField()
    categories = PackageCategorySerializerCyberstorm(many=True)
    results = PackageSerializerCyberstorm(many=True)


class PackageVersionExtendedSerializerCyberstorm(PackageVersionSerializerCyberstorm):
    name = serializers.CharField(max_length=Package._meta.get_field("name").max_length)
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length
    )
    community = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length
    )
    short_description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length
    )
    image_source = serializers.CharField(allow_null=True)
    size = serializers.IntegerField()
    author = serializers.CharField(max_length=Team._meta.get_field("name").max_length)
    is_pinned = serializers.BooleanField()
    is_nsfw = serializers.BooleanField()
    is_deprecated = serializers.BooleanField()
    description = serializers.CharField()
    github_link = serializers.CharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length
    )
    donation_link = serializers.CharField()
    dependency_string = serializers.CharField(max_length=210)
    team = PackageTeamSerializerCyberstorm()
