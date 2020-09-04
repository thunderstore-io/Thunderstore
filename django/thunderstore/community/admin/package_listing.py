from django.contrib import admin


from ..models.package_listing import PackageListing


@admin.register(PackageListing)
class PackageCategoryAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "categories",
    )
    list_filter = (
        "categories",
        "has_nsfw_content",
    )
    list_display = (
        "id",
        "package",
        "has_nsfw_content",
        "datetime_created",
        "datetime_updated",
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
