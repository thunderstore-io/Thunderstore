from rest_framework import serializers


class CyberstormCommunitySerializer(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    description = serializers.CharField(required=False)
    discord_url = serializers.CharField(required=False)
    datetime_created = serializers.DateTimeField()
    background_image_url = serializers.CharField(required=False)
    icon_url = serializers.CharField(required=False)
    total_download_count = serializers.IntegerField()
    total_package_count = serializers.IntegerField()
