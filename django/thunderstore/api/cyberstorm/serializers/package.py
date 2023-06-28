from rest_framework import serializers

from thunderstore.community.models import Community
from thunderstore.repository.models import Namespace, Package, PackageVersion, Team


class PackageTeamMemberSerializerCyberstorm(serializers.Serializer):
    user = serializers.CharField()
    image_source = serializers.CharField(allow_null=True)
    role = serializers.CharField()


class PackageTeamSerializerCyberstorm(serializers.Serializer):
    name = serializers.CharField()
    members = PackageTeamMemberSerializerCyberstorm(many=True)


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
