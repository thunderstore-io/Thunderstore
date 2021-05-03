from django.contrib import admin

from ..forms import PackageListingForm
from ..models.package_listing import PackageListing


@admin.register(PackageListing)
class PackageListingAdmin(admin.ModelAdmin):
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
        "package__owner__name",
        "package__name",
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
