from django.contrib import admin

from ..models.package_category import PackageCategory


@admin.register(PackageCategory)
class PackageCategoryAdmin(admin.ModelAdmin):
    list_filter = ("community", "hidden")
    list_display = (
        "id",
        "name",
        "slug",
        "hidden",
        "datetime_created",
        "datetime_updated",
        "community",
    )
    list_display_links = (
        "id",
        "name",
        "slug",
    )
    search_fields = (
        "name",
        "slug",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
        "community",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []
