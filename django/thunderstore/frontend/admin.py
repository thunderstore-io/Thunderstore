from django.contrib import admin

from thunderstore.frontend.models import CommunityNavLink, DynamicHTML, NavLink


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


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )
    list_display = (
        "pk",
        "title",
        "href",
        "order",
        "datetime_created",
        "datetime_updated",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "title",
        "href",
    )


@admin.register(CommunityNavLink)
class CommunityNavLinkAdmin(NavLinkAdmin):
    raw_id_fields = ("community",)
    list_display = (
        "pk",
        "community",
        "title",
        "href",
        "order",
        "datetime_created",
        "datetime_updated",
        "is_active",
    )
    search_fields = (
        "community__name",
        "title",
        "href",
    )
