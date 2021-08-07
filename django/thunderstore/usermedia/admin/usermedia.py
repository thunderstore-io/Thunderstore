from django.contrib import admin

from ..models.usermedia import UserMedia


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    filter_horizontal = ()
    raw_id_fields = ("owner",)
    list_filter = ("status",)
    list_display = (
        "uuid",
        "owner",
        "filename",
        "size",
        "prefix",
        "status",
        "datetime_created",
        "datetime_updated",
        "expiry",
    )
    list_display_links = ("uuid",)
    search_fields = ("uuid", "filename")
    readonly_fields = (
        "uuid",
        "prefix",
        "status",
        "upload_id",
    )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
