from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from thunderstore.storage.admin.mixins import ReadOnlyInline
from thunderstore.storage.models import DataBlobGroup, DataBlobReference


class DataBlobReferenceInline(ReadOnlyInline, admin.TabularInline):
    model = DataBlobReference
    fields = (
        "name",
        "data_size",
        "file",
    )
    readonly_fields = (
        "data_size",
        "file",
    )

    def file(self, obj: DataBlobReference):
        return mark_safe(f'<a href="{obj.data_url}">{obj.blob.data}</a>')


@admin.register(DataBlobGroup)
class DataBlobGroupAdmin(admin.ModelAdmin):
    inlines = [
        DataBlobReferenceInline,
    ]
    list_display = (
        "name",
        "is_complete",
        "datetime_created",
    )
    list_filter = ("is_complete",)
    search_fields = ("name",)
    date_hierarchy = "datetime_created"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
