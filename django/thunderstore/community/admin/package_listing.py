from django.contrib import admin

from ..models.package_listing import PackageListing


@admin.register(PackageListing)
class PackageCategoryAdmin(admin.ModelAdmin):
    filter_horizontal = ("categories",)
    raw_id_fields = ("package",)
    list_filter = (
        "categories",
        "has_nsfw_content",
        "community",
    )
    list_display = (
        "id",
        "package",
        "has_nsfw_content",
        "datetime_created",
        "datetime_updated",
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
        "datetime_created",
        "datetime_updated",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []
