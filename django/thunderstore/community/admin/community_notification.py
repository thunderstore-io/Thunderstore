from django.contrib import admin

from ..models import CommunityNotification


@admin.register(CommunityNotification)
class CommunityNotificationAdmin(admin.ModelAdmin):
    raw_id_fields = ("community",)
    list_display = (
        "community",
        "datetime_created",
        "datetime_updated",
    )
    list_display_links = ("community",)
    search_fields = ("community__identifier", "community__name")
    readonly_fields = (
        "datetime_created",
        "datetime_updated",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("community",)
        return self.readonly_fields
