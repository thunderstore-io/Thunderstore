from django.contrib import admin
from django.http import HttpRequest

from thunderstore.repository.models import AsyncPackageSubmission


@admin.register(AsyncPackageSubmission)
class AsyncPackageSubmissionAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "owner",
        "file",
    )
    list_select_related = (
        "owner",
        "file",
    )
    list_display = (
        "owner",
        "file",
        "status",
        "datetime_scheduled",
        "datetime_polled",
        "datetime_finished",
    )
    list_filter = ("status",)
    search_fields = ("owner__username",)

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
