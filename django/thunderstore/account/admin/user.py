from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.http import HttpRequest
from social_django.models import UserSocialAuth

from thunderstore.account.models import ServiceAccount, UserSettings
from thunderstore.community.models import CommunityMembership
from thunderstore.repository.models import TeamMember

User = get_user_model()


class ServiceAccountFilter(SimpleListFilter):
    title = "service account status"
    parameter_name = "is_service_account"

    def lookups(self, request: HttpRequest, model_admin):
        return [
            ("1", "Yes"),
            ("0", "No"),
        ]

    def queryset(self, request: HttpRequest, queryset):
        if self.value() == "0":
            return queryset.exclude(~Q(service_account=None))
        elif self.value() == "1":
            return queryset.exclude(service_account=None)


class ReadOnlyInline:
    extra = 0

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


class UserSettingsInline(ReadOnlyInline, admin.StackedInline):
    model = UserSettings


class TeamMembershipInline(ReadOnlyInline, admin.TabularInline):
    verbose_name = "team membership"
    verbose_name_plural = "team memberships"
    model = TeamMember


class CommunityMembershipInline(ReadOnlyInline, admin.TabularInline):
    verbose_name = "community membership"
    verbose_name_plural = "community memberships"
    model = CommunityMembership


class SocialAuthInline(ReadOnlyInline, admin.TabularInline):
    model = UserSocialAuth
    fields = ["provider", "uid"]


class UserAdmin(DjangoUserAdmin):
    inlines = (
        *DjangoUserAdmin.inlines,
        UserSettingsInline,
        TeamMembershipInline,
        CommunityMembershipInline,
        SocialAuthInline,
    )
    search_fields = (
        *DjangoUserAdmin.search_fields,
        "social_auth__uid",
    )
    list_filter = (
        *DjangoUserAdmin.list_filter,
        ServiceAccountFilter,
    )
    list_display = (
        *DjangoUserAdmin.list_display,
        "is_service_account",
    )
    date_hierarchy = "date_joined"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .annotate(
                is_service_account=Exists(
                    ServiceAccount.objects.filter(user=OuterRef("pk"))
                )
            )
        )

    def is_service_account(self, obj):
        return obj.is_service_account

    is_service_account.boolean = True
    is_service_account.admin_order_field = "is_service_account"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
