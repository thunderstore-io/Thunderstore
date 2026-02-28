from django.contrib import admin
from django.http import HttpRequest

from thunderstore.account.models.user_meta import UserMeta


@admin.register(UserMeta)
class UserMetaAdmin(admin.ModelAdmin):
    fields = (
        "user",
        "can_moderate_any_community",
    )
    readonly_fields = (
        "user",
        "can_moderate_any_community",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
