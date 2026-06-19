from django.contrib import admin

from ..models.moderator_note import ModeratorNote


@admin.register(ModeratorNote)
class ModeratorNoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target_type",
        "community",
        "package_listing",
        "package_version",
        "author",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = ("id",)
    list_select_related = (
        "community",
        "package_listing",
        "package_listing__package",
        "package_version",
        "package_version__package",
        "author",
    )
    raw_id_fields = (
        "community",
        "package_listing",
        "package_version",
        "author",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )
    search_fields = (
        "content",
        "community__identifier",
        "package_listing__package__name",
        "package_version__package__name",
    )
