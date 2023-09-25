from django.contrib import admin
from django.http import HttpRequest

from thunderstore.storage.admin.mixins import ReadOnlyInline
from thunderstore.storage.models import DataBlob, DataBlobReference


class DataBlobReferenceInline(ReadOnlyInline, admin.TabularInline):
    model = DataBlobReference
    fields = (
        "name",
        "group",
    )


@admin.register(DataBlob)
class DataBlobAdmin(admin.ModelAdmin):
    inlines = [
        DataBlobReferenceInline,
    ]
    readonly_fields = ("data", "checksum_sha256")
    list_display = (
        "checksum_sha256",
        "data_size",
        "is_deleted",
    )
    list_filter = ("is_deleted",)
    search_fields = ("checksum_sha256",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
