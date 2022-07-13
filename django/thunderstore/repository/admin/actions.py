from django.db import transaction
from django.db.models import QuerySet


@transaction.atomic
def activate(modeladmin, request, queryset: QuerySet):
    for package in queryset:
        package.is_active = True
        package.save(update_fields=("is_active",))


activate.short_description = "Activate"


@transaction.atomic
def deactivate(modeladmin, request, queryset: QuerySet):
    for package in queryset:
        package.is_active = False
        package.save(update_fields=("is_active",))


deactivate.short_description = "Deactivate"
