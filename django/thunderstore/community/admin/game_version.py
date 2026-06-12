from django.contrib import admin

from ..models.game_version import GameVersion, ReleaseGroup


@admin.register(ReleaseGroup)
class ReleaseGroupAdmin(admin.ModelAdmin):
    raw_id_fields = ("community",)
    list_filter = ("community",)
    list_display = (
        "id",
        "slug",
        "display_name",
        "release_name",
        "order",
        "datetime_created",
        "datetime_updated",
        "community",
    )
    list_display_links = (
        "id",
        "slug",
        "display_name",
        "release_name",
    )
    search_fields = (
        "slug",
        "display_name",
        "release_name",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
        "community",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []


@admin.register(GameVersion)
class GameVersionAdmin(admin.ModelAdmin):
    raw_id_fields = ("community", "release_group")
    list_filter = ("community", "release_group", "is_active")
    list_display = (
        "id",
        "version",
        "release_name",
        "order",
        "is_active",
        "datetime_created",
        "datetime_updated",
        "community",
        "release_group",
    )
    list_display_links = (
        "id",
        "version",
        "release_name",
    )
    search_fields = (
        "version",
        "release_name",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
        "community",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []
