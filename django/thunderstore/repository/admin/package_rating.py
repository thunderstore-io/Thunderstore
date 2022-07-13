from django.contrib import admin
from django.http import HttpRequest

from thunderstore.repository.models import PackageRating


@admin.register(PackageRating)
class PackageRatingAdmin(admin.ModelAdmin):
    model = PackageRating
    list_display = (
        "rater",
        "package",
        "date_created",
    )
    list_select_related = (
        "package",
        "rater",
    )
    raw_id_fields = (
        "package",
        "rater",
    )

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
