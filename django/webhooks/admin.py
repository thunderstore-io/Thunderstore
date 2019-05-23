from django.contrib import admin


from webhooks.models import Webhook


@admin.register(Webhook)
class PackageAdmin(admin.ModelAdmin):
    readonly_fields = ("date_created", "uuid4")
    list_display = ("name", "date_created", "webhook_type", "is_active")
    list_filter = ("is_active",)
