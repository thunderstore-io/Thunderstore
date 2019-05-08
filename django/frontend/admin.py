from django.contrib import admin


from frontend.models import DynamicHTML


@admin.register(DynamicHTML)
class DynamicHTML(admin.ModelAdmin):
    readonly_fields = (
        "date_created",
        "date_modified",
    )
    list_display = (
        "name",
        "placement",
        "date_created",
        "date_modified",
        "is_active",
    )
    list_filter = (
        "is_active",
        "placement",
    )
