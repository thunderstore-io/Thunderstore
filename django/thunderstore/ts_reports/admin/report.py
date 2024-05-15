from django.contrib import admin
from django.http import HttpRequest

from thunderstore.ts_reports.models import PackageReport


@admin.register(PackageReport)
class PackageReportAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    # list_display = (
    #     "thunderstore_user",
    #     "label",
    #     "discord_user_id",
    #     "can_deprecate",
    # )
    # list_select_related = ("thunderstore_user",)
    # list_filter = ("can_deprecate",)
    # search_fields = (
    #     "label",
    #     "thunderstore_user__username",
    # )
