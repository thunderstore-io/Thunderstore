from django.contrib import admin

from thunderstore.webhooks.forms.webhook import WebhookForm
from thunderstore.webhooks.models.audit import AuditWebhook
from thunderstore.webhooks.models.release import Webhook


@admin.register(Webhook)
class ReleaseWebhookAdmin(admin.ModelAdmin):
    form = WebhookForm

    readonly_fields = (
        "date_created",
        "uuid4",
    )
    filter_horizontal = (
        "exclude_categories",
        "require_categories",
    )
    search_fields = (
        "name",
        "community__name",
    )
    list_display = (
        "name",
        "date_created",
        "webhook_type",
        "is_active",
        "community",
    )
    raw_id_fields = ("community",)
    list_filter = ("is_active",)


@admin.register(AuditWebhook)
class AuditWebhookAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    filter_horizontal = ("match_communities",)
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )
    list_display = (
        "name",
        "datetime_created",
        "is_active",
    )
    list_filter = ("is_active",)
