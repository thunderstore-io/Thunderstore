from django.contrib import admin

from thunderstore.repository.models import DiscordUserBotPermission


@admin.register(DiscordUserBotPermission)
class DiscordUserBotPermissionAdmin(admin.ModelAdmin):
    raw_id_fields = ("thunderstore_user",)
    list_display = (
        "thunderstore_user",
        "label",
        "discord_user_id",
        "can_deprecate",
    )
    list_select_related = ("thunderstore_user",)
    list_filter = ("can_deprecate",)
    search_fields = (
        "label",
        "thunderstore_user__username",
    )
