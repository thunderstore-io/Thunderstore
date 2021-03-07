from rest_framework import serializers

from thunderstore.community.models import Community, PackageCategory


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = (
            "identifier",
            "name",
            "discord_url",
            "wiki_url",
        )


class PackageCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageCategory
        fields = (
            "name",
            "slug",
        )
