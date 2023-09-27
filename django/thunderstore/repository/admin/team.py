from django.contrib import admin

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.models import Team, TeamMember


class TeamMemberAdmin(admin.StackedInline):
    model = TeamMember
    extra = 0
    raw_id_fields = ("user",)
    list_display = (
        "user",
        "team",
        "role",
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    inlines = [
        TeamMemberAdmin,
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
