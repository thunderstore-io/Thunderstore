from django.contrib import admin

from .models import DatabaseCache


@admin.register(DatabaseCache)
class DatabaseCacheAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "key",
        "expires_on",
        "hits",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = (
        "id",
        "key",
    )
    search_fields = ("key",)
    exclude = ("content",)

    def has_change_permission(self, request, obj=None):
        return False
