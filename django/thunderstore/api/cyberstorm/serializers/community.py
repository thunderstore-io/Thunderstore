from rest_framework import serializers


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

    def get_total_download_count(self, obj) -> int:
        return obj.aggregated.download_count

    def get_total_package_count(self, obj) -> int:
        return obj.aggregated.package_count


class CyberstormPackageCategorySerializer(serializers.Serializer):
    id = serializers.CharField()  # noqa: A003
    name = serializers.CharField()
    slug = serializers.SlugField()


class CyberstormPackageListingSectionSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    priority = serializers.IntegerField()
