from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet

from ..forms import PackageListingForm
from ..models.package_listing import PackageListing, PackageListingReviewStatus


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
    actions = (
        approve_listing,
        reject_listing,
    )
    filter_horizontal = ("categories",)
    raw_id_fields = ("package",)
    list_filter = (
        "categories",
        "has_nsfw_content",
        "community",
        "review_status",
    )
    list_display = (
        "id",
        "package",
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
        "package__namespace__name",
        "package__name",
    )
    list_select_related = (
        "package",
        "package__owner",
        "package__namespace",
        "community",
    )
    readonly_fields = (
        "package",
        "community",
        "datetime_created",
        "datetime_updated",
    )
    form = PackageListingForm

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []
