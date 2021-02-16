from typing import Optional

from django.contrib import admin
from django.http import HttpRequest

from thunderstore.account.models import ServiceAccount


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = (
        "uuid",
        "nickname",
        "user",
        "owner",
        "created_at",
        "last_used",
    )
    list_filter = ()
    search_fields = ("user__username", "uuid", "owner__name")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Optional[ServiceAccount] = None
    ) -> bool:
        return False
