from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from thunderstore.storage.models import DataBlobReference


@admin.register(DataBlobReference)
class DataBlobReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "linked_group",
        "data_size",
        "content_type",
        "content_encoding",
        "datetime_created",
    )
    list_select_related = (
        "blob",
        "group",
    )
    list_filter = (
        "content_type",
        "content_encoding",
    )
    search_fields = (
        "group__name",
        "name",
        "blob__checksum_sha256",
    )
    readonly_fields = ("file",)
    date_hierarchy = "datetime_created"

    def file(self, obj: DataBlobReference):
        return mark_safe(f'<a href="{obj.data_url}">{obj.blob.data}</a>')

    def linked_group(self, obj: DataBlobReference):
        return mark_safe(f'<a href="{obj.group.get_admin_url()}">{obj.group}</a>')

    linked_group.short_description = "group"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
