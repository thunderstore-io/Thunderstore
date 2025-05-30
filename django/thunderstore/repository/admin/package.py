from html import escape
from typing import Optional

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.models import Package, PackageVersion


class PackageVersionInline(admin.StackedInline):
    model = PackageVersion
    fields = (
        "is_active",
        "version_link",
        "date_created",
        "description",
        "downloads",
        "file",
        "file_size",
        "format_spec",
        "icon",
        "file_tree_link",
        "uploaded_by",
        "visibility",
        "website_url",
    )
    readonly_fields = (
        "version_link",
        "date_created",
        "description",
        "downloads",
        "file",
        "file_size",
        "format_spec",
        "icon",
        "file_tree_link",
        "uploaded_by",
        "visibility",
        "website_url",
    )
    extra = 0

    def has_add_permission(self, request: HttpRequest, obj) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def version_link(self, obj):
        return mark_safe(f'<a href="{obj.get_admin_url()}">{escape(str(obj))}</a>')

    version_link.short_description = "Version"

    def file_tree_link(self, obj):
        if not obj.file_tree:
            return None
        return mark_safe(
            f'<a href="{obj.file_tree.get_admin_url()}">{escape(str(obj.file_tree))}</a>'
        )

    file_tree_link.short_description = "File Tree"


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

    fields = (
        "is_active",
        "is_deprecated",
        "is_pinned",
        "show_decompilation_results",
        "date_created",
        "downloads",
        "name",
        "namespace",
        "owner",
        "latest",
        "visibility",
    )
    readonly_fields = (
        "date_created",
        "downloads",
        "name",
        "namespace",
        "owner",
        "latest",
        "visibility",
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
