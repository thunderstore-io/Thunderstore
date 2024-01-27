from django.contrib import admin
from django.http import HttpRequest

from thunderstore.repository.models import PackageInstaller


@admin.register(PackageInstaller)
class PackageInstallerAdmin(admin.ModelAdmin):
    readonly_fields = ("identifier",)
    list_display_links = ("pk", "identifier")
    list_display = ("pk", "identifier")
    search_fields = ("pk", "identifier")

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
