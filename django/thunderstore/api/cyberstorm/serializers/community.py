from rest_framework import serializers

from thunderstore.api.cyberstorm.serializers.moderator_note import (
    ModeratorNoteSerializer,
)


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

    def get_total_download_count(self, obj) -> int:
        return obj.aggregated.download_count

    def get_total_package_count(self, obj) -> int:
        return obj.aggregated.package_count


class CyberstormCommunityDetailSerializer(CyberstormCommunitySerializer):
    """
    Community detail payload. Adds the community's active moderator notes,
    surfaced only on the single-community detail view (never the community list,
    to avoid an N+1 across every community).
    """

    moderator_notes = ModeratorNoteSerializer(
        source="display_moderator_notes", many=True
    )


class CommunityModeratorPermissionsSerializer(serializers.Serializer):
    can_moderate = serializers.BooleanField()


class CommunityPermissionsSerializer(serializers.Serializer):
    """The requesting user's community-level permissions (e.g. moderation)."""

    permissions = CommunityModeratorPermissionsSerializer()


class CyberstormPackageCategorySerializer(serializers.Serializer):
    id = serializers.CharField()  # noqa: A003
    name = serializers.CharField()
    slug = serializers.SlugField()


class CyberstormPackageListingSectionSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    priority = serializers.IntegerField()
