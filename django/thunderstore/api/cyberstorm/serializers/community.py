from rest_framework import serializers

from thunderstore.api.cyberstorm.serializers.shared import (
    CyberstormPackageCategorySerializer,
)


class CyberstormCommunitySerializer(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    description = serializers.CharField(required=False)
    discord_url = serializers.CharField(required=False)
    datetime_created = serializers.DateTimeField()
    background_image_url = serializers.CharField(required=False)
    icon_url = serializers.CharField(required=False)
    total_download_count = serializers.SerializerMethodField()
    total_package_count = serializers.SerializerMethodField()
    package_categories = CyberstormPackageCategorySerializer(many=True)

    def get_total_download_count(self, obj) -> int:
        return obj.aggregated.download_count

    def get_total_package_count(self, obj) -> int:
        return obj.aggregated.package_count
