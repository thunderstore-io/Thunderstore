from django.contrib import admin

from thunderstore.modpacks.models import LegacyProfile


@admin.register(LegacyProfile)
class LegacyProfileAdmin(admin.ModelAdmin):
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
        "file",
        "file_size",
    )
    list_display = (
        "id",
        "file_size",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = ("id",)
    date_hierarchy = "datetime_created"
    search_fields = ("id",)
