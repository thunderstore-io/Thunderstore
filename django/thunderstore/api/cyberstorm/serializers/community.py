from rest_framework import serializers


class CyberstormCommunitySerializer(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    total_download_count = serializers.IntegerField()
    total_package_count = serializers.IntegerField()
    background_image_url = serializers.CharField(required=False)
    description = serializers.CharField()
    discord_url = serializers.CharField(required=False)
