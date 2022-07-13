from django.contrib import admin
from django.http import HttpRequest

from thunderstore.repository.models import PackageVersion


@admin.register(PackageVersion)
class PackageVersionAdmin(admin.ModelAdmin):
    model = PackageVersion
    list_select_related = (
        "package",
        "package__owner",
        "package__namespace",
    )
    list_filter = ("is_active", "date_created")
    list_display = (
        "package",
        "version_number",
        "is_active",
        "file_size",
        "downloads",
        "date_created",
    )
    search_fields = (
        "package__owner__name",
        "package__namespace__name",
        "version_number",
    )
    date_hierarchy = "date_created"
    readonly_fields = [x.name for x in PackageVersion._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
