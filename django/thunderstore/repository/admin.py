from typing import Optional

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest

from thunderstore.repository.models import (
    DiscordUserBotPermission,
    Package,
    PackageRating,
    PackageVersion,
    UploaderIdentity,
    UploaderIdentityMember,
)


@admin.register(PackageRating)
class PackageRatingAdmin(admin.ModelAdmin):
    model = PackageRating
    list_display = (
        "rater",
        "package",
        "date_created",
    )


class UploaderIdentityMemberAdmin(admin.StackedInline):
    model = UploaderIdentityMember
    extra = 0
    raw_id_fields = ("user",)
    list_display = (
        "user",
        "identity",
        "role",
    )


@admin.register(UploaderIdentity)
class UploaderIdentityAdmin(admin.ModelAdmin):
    inlines = [
        UploaderIdentityMemberAdmin,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []

    readonly_fields = ("name",)
    list_display = ("name",)


class PackageVersionInline(admin.StackedInline):
    model = PackageVersion
    readonly_fields = (
        "date_created",
        "dependencies",
        "description",
        "downloads",
        "file",
        "file_size",
        "icon",
        "name",
        "readme",
        "version_number",
        "website_url",
    )
    extra = 0
    filter_horizontal = ("dependencies",)

    def has_add_permission(self, request: HttpRequest, obj) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@transaction.atomic
def deprecate_package(modeladmin, request, queryset: QuerySet[Package]):
    for package in queryset:
        package.is_deprecated = True
        package.save(update_fields=("is_deprecated",))


deprecate_package.short_description = "Deprecate"


@transaction.atomic
def undeprecate_package(modeladmin, request, queryset: QuerySet[Package]):
    for package in queryset:
        package.is_deprecated = False
        package.save(update_fields=("is_deprecated",))


undeprecate_package.short_description = "Undeprecate"


@transaction.atomic
def deactivate_package(modeladmin, request, queryset: QuerySet[Package]):
    for package in queryset:
        package.is_active = False
        package.save(update_fields=("is_active",))


deactivate_package.short_description = "Deactivate"


@transaction.atomic
def activate_package(modeladmin, request, queryset: QuerySet[Package]):
    for package in queryset:
        package.is_active = True
        package.save(update_fields=("is_active",))


activate_package.short_description = "Activate"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    inlines = [
        PackageVersionInline,
    ]
    actions = (
        deprecate_package,
        undeprecate_package,
        deactivate_package,
        activate_package,
    )

    readonly_fields = (
        "date_created",
        "downloads",
        "name",
        "owner",
        "latest",
    )
    list_display = (
        "name",
        "owner",
        "is_active",
        "is_deprecated",
        "is_pinned",
    )
    list_filter = (
        "is_active",
        "is_pinned",
        "is_deprecated",
    )
    search_fields = (
        "name",
        "owner__name",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Optional[Package] = None
    ) -> bool:
        return False


@admin.register(DiscordUserBotPermission)
class DiscordUserBotPermissionAdmin(admin.ModelAdmin):
    raw_id_fields = ("thunderstore_user",)
    list_display = (
        "thunderstore_user",
        "label",
        "discord_user_id",
        "can_deprecate",
    )
    list_filter = ("can_deprecate",)
    search_fields = (
        "label",
        "thunderstore_user__username",
    )
