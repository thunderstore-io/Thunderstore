from django.contrib import admin


from repository.models import Package
from repository.models import PackageVersion


class PackageVersionInline(admin.StackedInline):
    model = PackageVersion
    readonly_fields = (
        "website_url",
        "date_created",
        "name",
        "version_number",
        "website_url",
        "file",
        "icon",
    )
    extra = 0


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    inlines = [
        PackageVersionInline,
    ]

    readonly_fields = (
        "name",
        "owner",
        "date_created",
    )
    list_display = (
        "name",
        "owner",
        "is_active",
        "is_pinned",
    )
    list_filter = (
        "is_active",
        "is_pinned",
    )
