from django.contrib import admin

from thunderstore.core.models import IncomingJWTAuthConfiguration


@admin.register(IncomingJWTAuthConfiguration)
class PackageAdmin(admin.ModelAdmin):
    readonly_fields = ("key_id",)
    list_display = (
        "name",
        "user",
        "secret_type",
        "key_id",
    )
    list_filter = ("secret_type",)
    search_fields = (
        "key_id",
        "user__username",
    )
