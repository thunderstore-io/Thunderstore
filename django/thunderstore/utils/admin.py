from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet


class AdminActions:
    @transaction.atomic
    def deactivate(modeladmin, request, queryset: QuerySet):
        for obj in queryset:
            obj.is_active = False
            obj.save(update_fields=("is_active",))

    deactivate.short_description = "Deactivate"

    @transaction.atomic
    def activate(modeladmin, request, queryset: QuerySet):
        for obj in queryset:
            obj.is_active = True
            obj.save(update_fields=("is_active",))

    activate.short_description = "Activate"

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

    @transaction.atomic
    def deprecate(modeladmin, request, queryset: QuerySet):
        for obj in queryset:
            obj.is_deprecated = True
            obj.save(update_fields=("is_deprecated",))

    deprecate.short_description = "Deprecate"

    @transaction.atomic
    def undeprecate(modeladmin, request, queryset: QuerySet):
        for obj in queryset:
            obj.is_deprecated = False
            obj.save(update_fields=("is_deprecated",))

    undeprecate.short_description = "Undeprecate"
