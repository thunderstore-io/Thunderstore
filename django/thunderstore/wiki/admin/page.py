from django.contrib import admin

from thunderstore.wiki.models import WikiPage


@admin.register(WikiPage)
class WikiPageAdmin(admin.ModelAdmin):
    search_fields = (
        "pk",
        "wiki__title",
        "title",
    )
    list_select_related = ("wiki",)
    list_display = (
        "pk",
        "wiki",
        "title",
        "slug",
    )

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False
