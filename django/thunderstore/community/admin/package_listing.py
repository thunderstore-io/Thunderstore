from html import escape
from typing import Optional

from django.contrib import admin
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from ..consts import PackageListingReviewStatus
from ..forms import PackageListingAdminForm
from ..models.community import Community
from ..models.package_listing import PackageListing


@transaction.atomic
def reject_listing(modeladmin, request, queryset: QuerySet[PackageListing]):
    for listing in queryset:
        listing.reject(
            agent=request.user, rejection_reason="Invalid submission", is_system=False
        )


reject_listing.short_description = "Reject"


@transaction.atomic
def approve_listing(modeladmin, request, queryset: QuerySet[PackageListing]):
    for listing in queryset:
        listing.approve(agent=request.user, is_system=False)


approve_listing.short_description = "Approve"


class CommunityFilter(admin.SimpleListFilter):
    title = "Community"
    parameter_name = "community"

    def lookups(self, request: HttpRequest, model_admin):
        return Community.objects.order_by("name").values_list("identifier", "name")

    def queryset(self, request: HttpRequest, queryset: QuerySet[PackageListing]):
        if self.value():
            return queryset.exclude(~Q(community__identifier=self.value()))


@admin.register(PackageListing)
class PackageListingAdmin(admin.ModelAdmin):
    form = PackageListingAdminForm
    actions = (
        approve_listing,
        reject_listing,
    )

    fields = (
        "categories",
        "is_review_requested",
        "review_status",
        "rejection_reason",
        "notes",
        "has_nsfw_content",
        "is_auto_imported",
        "package_link",
        "community",
        "datetime_created",
        "datetime_updated",
        "visibility",
    )
    readonly_fields = (
        "package_link",
        "community",
        "datetime_created",
        "datetime_updated",
        "visibility",
    )
    filter_horizontal = ("categories",)
    raw_id_fields = ("package", "community")
    list_filter = (
        "has_nsfw_content",
        "is_review_requested",
        "review_status",
        CommunityFilter,
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
    )
    list_select_related = (
        "package",
        "package__owner",
        "package__namespace",
        "community",
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
