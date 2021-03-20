from django import forms
from django.contrib import admin
from django.forms import PasswordInput, TextInput

from ..models.community_site import CommunitySite


class CommunitySiteAdminForm(forms.ModelForm):
    class Meta:
        model = CommunitySite
        widgets = {
            "social_auth_discord_key": TextInput(attrs={"size": 40}),
            "social_auth_discord_secret": PasswordInput(
                render_value=True, attrs={"size": 40}
            ),
            "social_auth_github_key": TextInput(attrs={"size": 40}),
            "social_auth_github_secret": PasswordInput(
                render_value=True, attrs={"size": 40}
            ),
        }
        fields = "__all__"


@admin.register(CommunitySite)
class CommunitySiteAdmin(admin.ModelAdmin):
    form = CommunitySiteAdminForm

    filter_horizontal = ()
    list_filter = ("is_listed",)
    list_display = (
        "id",
        "community",
        "site",
        "is_listed",
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
        "icon_width",
        "icon_height",
        "background_image_width",
        "background_image_height",
    )
