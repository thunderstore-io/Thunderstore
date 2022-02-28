from django.contrib import admin

from thunderstore.ts_github.models import KeyProvider, StoredPublicKey
from thunderstore.utils.admin import AdminActions


@admin.register(StoredPublicKey)
class StoredPublicKeyAdmin(admin.ModelAdmin, AdminActions):
    actions = (
        AdminActions.activate,
        AdminActions.deactivate,
    )
    list_display = ("key_identifier", "key_type", "is_active", "provider")
    list_filter = ("is_active", "key_type", "provider")
    search_fields = ("key_identifier", "key")


@admin.register(KeyProvider)
class KeyProviderAdmin(admin.ModelAdmin):
    list_display = ("identifier", "datetime_last_synced")
    search_fields = ("identifier", "provider_url")
