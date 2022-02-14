from rest_framework import serializers

from thunderstore.community.models import Community


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


class FrontPageContentSerializer(serializers.Serializer):
    """
    Front page contains general and community specific stats.
    """

    communities = CommunityCardSerializer(many=True)
    download_count = serializers.IntegerField(min_value=0)
    package_count = serializers.IntegerField(min_value=0)
