from django.contrib import admin
from django.http import HttpRequest

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.models import Namespace


@admin.register(Namespace)
class NamespaceAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []

    raw_id_fields = ("team",)
    actions = (
        activate,
        deactivate,
    )
    readonly_fields = ("name",)
    list_select_related = ("team",)
    list_display = ("name", "is_active", "team")
    list_filter = ("is_active",)
    search_fields = ("name", "team__name")

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
