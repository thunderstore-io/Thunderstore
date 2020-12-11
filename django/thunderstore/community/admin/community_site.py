from django.contrib import admin

from ..models.community_site import CommunitySite


@admin.register(CommunitySite)
class CommunitySiteAdmin(admin.ModelAdmin):
    filter_horizontal = (
    )
    list_filter = (
    )
    list_display = (
        "id",
        "community",
        "site",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = (
        "id",
        "community",
        "site",
    )
    search_fields = (
        "community__identifier",
        "community__name",
        "site__domain",
        "site__name",
    )
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )
