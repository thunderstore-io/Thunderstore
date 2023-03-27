from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from thunderstore.wiki.models import Wiki, WikiPage


class WikiPageInline(admin.TabularInline):
    model = WikiPage
    readonly_fields = ("admin_link",)
    exclude = ("markdown_content",)
    extra = 0

    def admin_link(self, instance):
        url = reverse(
            f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change",
            args=(instance.id,),
        )
        return format_html(f'<a href="{url}">View details</a>')

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False


@admin.register(Wiki)
class WikiAdmin(admin.ModelAdmin):
    search_fields = (
        "pk",
        "title",
    )
    list_display = (
        "pk",
        "title",
        "slug",
    )
    inlines = (WikiPageInline,)

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False
