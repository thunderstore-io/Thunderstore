from django.contrib import admin

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.models import Team, TeamLog, TeamMember


class TeamMemberAdmin(admin.StackedInline):
    model = TeamMember
    extra = 0
    raw_id_fields = ("user",)
    list_display = (
        "user",
        "team",
        "role",
    )


class TeamLogAdmin(admin.TabularInline):
    model = TeamLog
    extra = 0
    readonly_fields = ("event", "performed_by", "target", "datetime_created")

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    inlines = [
        TeamMemberAdmin,
        TeamLogAdmin,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []

    actions = (
        activate,
        deactivate,
    )
    readonly_fields = ("name",)
    list_display = (
        "name",
        "is_active",
        "show_decompilation_results",
    )
    list_filter = (
        "is_active",
        "show_decompilation_results",
    )
    search_fields = ("name",)
