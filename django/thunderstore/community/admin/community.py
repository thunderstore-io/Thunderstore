from django.contrib import admin

from ...core.utils import ensure_fields_editable_on_creation
from ..models.community import Community


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    filter_horizontal = ()
    list_filter = ()
    list_display = (
        "id",
        "identifier",
        "name",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = (
        "id",
        "identifier",
        "name",
    )
    search_fields = (
        "identifier",
        "name",
    )
    readonly_fields = (
        "identifier",
        "datetime_created",
        "datetime_updated",
    )

    def get_readonly_fields(self, request, obj=None):
        return ensure_fields_editable_on_creation(
            self.readonly_fields, obj, ("identifier",)
        )
