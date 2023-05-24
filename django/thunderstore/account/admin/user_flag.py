from django.contrib import admin
from django.http import HttpRequest

from thunderstore.account.models import UserFlag, UserFlagMembership


@admin.register(UserFlag)
class UserFlagAdmin(admin.ModelAdmin):
    date_hierarchy = "datetime_created"
    list_display = (
        "identifier",
        "name",
        "description",
        "app_label",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = (
        "identifier",
        "name",
    )
    list_filter = ("app_label",)
    search_fields = (
        "pk",
        "identifier",
        "name",
    )
    readonly_fields = (
        "identifier",
        "app_label",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(UserFlagMembership)
class UserFlagMembershipAdmin(admin.ModelAdmin):
    date_hierarchy = "datetime_valid_from"
    raw_id_fields = (
        "user",
        "flag",
    )
    list_display = (
        "user",
        "flag",
        "datetime_valid_from",
        "datetime_valid_until",
    )
    list_display_links = (
        "user",
        "flag",
    )
    list_select_related = ("flag",)
    list_filter = ("flag",)
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
        "related_object_id",
        "related_object_type",
        "related_object",
    )
    search_fields = (
        "user__username",
        "user__email",
        "flag__name",
        "flag__identifier",
    )
