from django.contrib import admin


from thunderstore.webhooks.models import Webhook


@admin.register(Webhook)
class PackageAdmin(admin.ModelAdmin):
    readonly_fields = (
        "date_created",
        "uuid4",
    )
    filter_horizontal = (
        "exclude_categories",
        "require_categories",
    )
    list_display = (
        "name",
        "date_created",
        "webhook_type",
        "is_active",
        "community_site",
    )
    list_filter = (
        "is_active",
        "community_site",
    )
