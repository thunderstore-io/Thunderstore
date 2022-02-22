from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet

from thunderstore.ts_github.models import KeyProvider, StoredPublicKey


@transaction.atomic
def deactivate(modeladmin, request, queryset: QuerySet):
    for key in queryset:
        key.is_active = False
        key.save(update_fields=("is_active",))


deactivate.short_description = "Deactivate"


@transaction.atomic
def activate(modeladmin, request, queryset: QuerySet):
    for key in queryset:
        key.is_active = True
        key.save(update_fields=("is_active",))


activate.short_description = "Activate"


@admin.register(StoredPublicKey)
class StoredPublicKeyAdmin(admin.ModelAdmin):
    actions = (
        activate,
        deactivate,
    )
    list_display = ("key_identifier", "key_type", "is_active")
    list_filter = ("is_active", "key_type")
    search_fields = ("key_identifier", "key")


@admin.register(KeyProvider)
class KeyProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "last_update_time")
    search_fields = ("name", "provider_url")
