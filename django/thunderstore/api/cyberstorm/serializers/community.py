from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers


class CyberstormCommunityNotificationSerializer(serializers.Serializer):
    type = serializers.CharField()  # noqa: A003
    content = serializers.CharField()


class CyberstormCommunitySerializer(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    short_description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    discord_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    wiki_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    datetime_created = serializers.DateTimeField()
    background_image_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    hero_image_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    cover_image_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    icon_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    community_icon_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    total_download_count = serializers.SerializerMethodField()
    total_package_count = serializers.SerializerMethodField()
    has_mod_manager_support = serializers.BooleanField()
    is_listed = serializers.BooleanField()
    notifications = serializers.SerializerMethodField()

    def get_total_download_count(self, obj) -> int:
        return obj.aggregated.download_count

    def get_total_package_count(self, obj) -> int:
        return obj.aggregated.package_count

    @swagger_serializer_method(
        serializer_or_field=CyberstormCommunityNotificationSerializer(many=True)
    )
    def get_notifications(self, obj):
        notification = getattr(obj, "notification", None)
        if notification is None:
            return []
        return CyberstormCommunityNotificationSerializer(
            notification.notifications, many=True
        ).data


class CyberstormPackageCategorySerializer(serializers.Serializer):
    id = serializers.CharField()  # noqa: A003
    name = serializers.CharField()
    slug = serializers.SlugField()


class CyberstormPackageListingSectionSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    priority = serializers.IntegerField()
