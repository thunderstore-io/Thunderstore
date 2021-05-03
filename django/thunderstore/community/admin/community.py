from django.contrib import admin

from ...core.utils import ensure_fields_editable_on_creation
from ..models.community import Community
from ..models.community_membership import CommunityMembership


class CommunityMembershipInline(admin.TabularInline):
    model = CommunityMembership
    raw_id_fields = ("user",)
    extra = 0


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    filter_horizontal = ()
    list_filter = ("is_listed",)
    list_display = (
        "id",
        "identifier",
        "name",
        "is_listed",
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
    inlines = (CommunityMembershipInline,)

    def get_readonly_fields(self, request, obj=None):
        return ensure_fields_editable_on_creation(
            self.readonly_fields, obj, ("identifier",)
        )
