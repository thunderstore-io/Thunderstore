from html import escape
from typing import Optional

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.utils.safestring import mark_safe

from ..consts import PackageListingReviewStatus
from ..forms import PackageListingAdminForm
from ..models.package_listing import PackageListing


@transaction.atomic
def reject_listing(modeladmin, request, queryset: QuerySet[PackageListing]):
    for listing in queryset:
        listing.review_status = PackageListingReviewStatus.rejected
        listing.save(update_fields=("review_status",))


reject_listing.short_description = "Reject"


@transaction.atomic
def approve_listing(modeladmin, request, queryset: QuerySet[PackageListing]):
    for listing in queryset:
        listing.review_status = PackageListingReviewStatus.approved
        listing.save(update_fields=("review_status",))


approve_listing.short_description = "Approve"


@admin.register(PackageListing)
class PackageListingAdmin(admin.ModelAdmin):
    form = PackageListingAdminForm
    actions = (
        approve_listing,
        reject_listing,
    )
    filter_horizontal = ("categories",)
    raw_id_fields = ("package", "community")
    list_filter = (
        "has_nsfw_content",
        "is_review_requested",
        "review_status",
        "community",
    )
    list_display = (
        "id",
        "package",
        "is_review_requested",
        "has_nsfw_content",
        "datetime_created",
        "datetime_updated",
        "review_status",
        "community",
    )
    list_display_links = (
        "id",
        "package",
    )
    search_fields = (
        "package__namespace__name",
        "package__owner__name",
        "package__name",
        "package__versions__file_tree__entries__blob__checksum_sha256",
    )
    list_select_related = (
        "package",
        "package__owner",
        "package__namespace",
        "community",
    )
    readonly_fields = (
        "package_link",
        "community",
        "datetime_created",
        "datetime_updated",
    )
    exclude = ("package",)

    def package_link(self, obj):
        return mark_safe(
            f'<a href="{obj.package.get_admin_url()}">{escape(str(obj.package))}</a>'
        )

    package_link.short_description = "Package"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []

    def get_exclude(self, request, obj=None):
        if obj:
            return self.exclude
        else:
            return []

    def get_view_on_site_url(
        self, obj: Optional[PackageListing] = None
    ) -> Optional[str]:
        if obj:
            return obj.get_full_url()
        return super().get_view_on_site_url(obj)
