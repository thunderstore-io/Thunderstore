from typing import Optional

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.models import Package, PackageVersion


class PackageVersionInline(admin.StackedInline):
    model = PackageVersion
    readonly_fields = (
        "date_created",
        "description",
        "downloads",
        "file",
        "file_size",
        "format_spec",
        "icon",
        "version_number",
        "website_url",
        "file_tree",
        "visibility",
    )
    exclude = ("readme", "changelog", "dependencies", "name")
    extra = 0

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


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    inlines = [
        PackageVersionInline,
    ]
    actions = (
        deprecate_package,
        undeprecate_package,
        deactivate,
        activate,
    )

    readonly_fields = (
        "date_created",
        "downloads",
        "name",
        "namespace",
        "owner",
        "latest",
    )
    list_display = (
        "name",
        "namespace",
        "is_active",
        "is_deprecated",
        "is_pinned",
        "file_size",
        "show_decompilation_results",
    )
    list_filter = (
        "is_active",
        "is_pinned",
        "is_deprecated",
        "show_decompilation_results",
    )
    search_fields = (
        "name",
        "namespace__name",
        "owner__name",
    )
    list_select_related = (
        "latest",
        "owner",
        "namespace",
    )

    def file_size(self, obj):
        return obj.latest.file_size if obj.latest else 0

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_view_on_site_url(self, obj: Optional[Package] = None) -> Optional[str]:
        if obj:
            return obj.get_view_on_site_url()
        return super().get_view_on_site_url(obj)

    def has_delete_permission(
        self, request: HttpRequest, obj: Optional[Package] = None
    ) -> bool:
        return False

    file_size.admin_order_field = "latest__file_size"
