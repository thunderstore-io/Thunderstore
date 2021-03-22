from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet

from ..forms import PackageListingSectionForm
from ..models import PackageListingSection


@transaction.atomic
def set_unlisted(modeladmin, request, queryset: QuerySet):
    for obj in queryset:
        obj.is_listed = False
        obj.save(update_fields=("is_listed",))


set_unlisted.short_description = "Set unlisted"


@transaction.atomic
def set_listed(modeladmin, request, queryset: QuerySet):
    for obj in queryset:
        obj.is_listed = True
        obj.save(update_fields=("is_listed",))


set_listed.short_description = "Set listed"


@admin.register(PackageListingSection)
class PackageListingSectionAdmin(admin.ModelAdmin):
    filter_horizontal = ("require_categories", "exclude_categories")
    raw_id_fields = ("community",)
    list_filter = (
        "community",
        "is_listed",
    )
    list_display = (
        "name",
        "slug",
        "is_listed",
        "priority",
        "datetime_created",
        "datetime_updated",
        "community",
    )
    list_display_links = (
        "name",
        "slug",
    )
    search_fields = (
        "name",
        "community__name",
        "require_categories__name",
        "exclude_categories__name",
    )
    readonly_fields = (
        "uuid",
        "slug",
        "community",
        "datetime_created",
        "datetime_updated",
    )
    actions = (
        set_listed,
        set_unlisted,
    )
    form = PackageListingSectionForm

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []
