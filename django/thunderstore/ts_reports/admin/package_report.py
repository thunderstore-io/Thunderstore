from html import escape

from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from thunderstore.ts_reports.models import PackageReport


def set_active(modeladmin, request, queryset):
    queryset.update(is_active=True)


def set_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.register(PackageReport)
class PackageReportAdmin(admin.ModelAdmin):
    actions = [
        set_active,
        set_inactive,
    ]

    list_display = (
        "get_details",
        "link_package",
        "link_listing",
        "link_version",
        "submitted_by",
        "datetime_created",
        "is_automated",
        "is_active",
    )
    ordering = ("-datetime_created",)
    list_filter = (
        "is_active",
        "is_automated",
        "category",
    )
    search_fields = (
        "package__name",
        "package__owner__name",
        "package_listing__community__name",
    )

    fields = (
        "is_active",
        "is_automated",
        "category",
        "reason",
        "description",
        "submitted_by",
        "link_package",
        "link_listing",
        "link_version",
        "datetime_created",
        "datetime_updated",
    )

    raw_id_fields = (
        "submitted_by",
        "package",
        "package_listing",
        "package_version",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )

    def get_details(self, obj):
        return f"{obj.category} : {obj.reason}"

    get_details.short_description = "Report"

    def link_package(self, obj):
        if obj.package:
            return mark_safe(
                f'<a href="{obj.package.get_admin_url()}">{escape(str(obj.package))}</a>'
            )
        return "-"

    link_package.short_description = "Package"

    def link_listing(self, obj):
        if obj.package_listing:
            return mark_safe(
                f'<a href="{obj.package_listing.get_admin_url()}">{escape(str(obj.package_listing.community.name))}</a>'
            )
        return "-"

    link_listing.short_description = "Listing"

    def link_version(self, obj):
        if obj.package_version:
            return mark_safe(
                f'<a href="{obj.package_version.get_admin_url()}">{escape(str(obj.package_version.version_number))}</a>'
            )
        return "-"

    link_version.short_description = "Version"

    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith("listing:"):
            search_id = search_term[8:]
            return queryset.filter(package_listing__id=search_id), True

        if search_term.startswith("package:"):
            search_id = search_term[8:]
            return queryset.filter(package__id=search_id), True

        if search_term.startswith("version:"):
            search_id = search_term[8:]
            return queryset.filter(package_version__id=search_id), True

        search_term = search_term.replace("-", " ")

        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        return queryset, use_distinct

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
