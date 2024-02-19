from django import forms
from django.contrib import admin

from thunderstore.frontend.models import (
    CommunityNavLink,
    DynamicHTML,
    FooterLink,
    NavLink,
)


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
class LinkAdmin(admin.ModelAdmin):
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
class CommunityNavLinkAdmin(LinkAdmin):
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


class FooterLinkAdminForm(forms.ModelForm):
    class Meta:
        model = FooterLink
        widgets = {
            "title": forms.TextInput(attrs={"size": 40}),
            "group_title": forms.TextInput(attrs={"size": 40}),
            "href": forms.TextInput(attrs={"size": 40}),
            "css_class": forms.TextInput(attrs={"size": 40}),
        }
        fields = "__all__"


@admin.register(FooterLink)
class FooterLinkAdmin(LinkAdmin):
    form = FooterLinkAdminForm
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )
    list_display = (
        "pk",
        "title",
        "group_title",
        "href",
        "order",
        "datetime_created",
        "datetime_updated",
        "is_active",
    )
    list_filter = (
        "is_active",
        "group_title",
    )
    search_fields = (
        "title",
        "href",
    )
