from django.contrib import admin

from thunderstore.frontend.models import DynamicHTML


@admin.register(DynamicHTML)
class DynamicHTML(admin.ModelAdmin):
    filter_horizontal = (
        "exclude_communities",
        "require_communities",
    )
    readonly_fields = (
        "date_created",
        "date_modified",
    )
    list_display = (
        "name",
        "ordering",
        "placement",
        "date_created",
        "date_modified",
        "is_active",
    )
    list_filter = (
        "is_active",
        "placement",
        "exclude_communities",
        "require_communities",
    )
