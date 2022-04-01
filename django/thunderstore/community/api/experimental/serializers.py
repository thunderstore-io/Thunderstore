from rest_framework import serializers

from thunderstore.community.models import Community


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
