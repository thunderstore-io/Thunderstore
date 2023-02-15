from typing import List, Optional, Tuple, Union

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from django_contracts.models import (
    LegalContract,
    LegalContractVersion,
    PublishableMixin,
)
from django_contracts.models.publishable import PublishStatus


def publish(modeladmin, request, queryset: QuerySet[PublishableMixin]) -> None:
    for obj in queryset:
        obj.publish()


publish.short_description = "Publish"


@admin.register(LegalContract)
class LegalContractAdmin(admin.ModelAdmin):
    actions = (publish,)
    readonly_fields = (
        "datetime_published",
        "publish_status",
        "latest",
    )

    list_display = (
        "__str__",
        "publish_status",
        "datetime_published",
    )
    list_filter = ("publish_status",)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[LegalContract] = None
    ) -> Union[List[str], Tuple]:
        if not obj or obj.publish_status != PublishStatus.PUBLISHED:
            return self.readonly_fields
        return self.readonly_fields + ("slug",)

    def has_delete_permission(
        self, request: HttpRequest, obj: Optional[PublishableMixin] = None
    ) -> bool:
        if obj and obj.publish_status != PublishStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(LegalContractVersion)
class LegalContractVersionAdmin(admin.ModelAdmin):
    actions = (publish,)
    readonly_fields = (
        "datetime_published",
        "publish_status",
    )

    list_select_related = ("contract",)
    list_display = (
        "__str__",
        "publish_status",
        "datetime_published",
    )
    list_filter = ("publish_status",)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[LegalContractVersion] = None
    ) -> Union[List[str], Tuple]:
        if not obj or obj.publish_status != PublishStatus.PUBLISHED:
            return self.readonly_fields
        return self.readonly_fields + (
            "html_content",
            "markdown_content",
            "contract",
        )

    def has_change_permission(
        self, request: HttpRequest, obj: Optional[PublishableMixin] = None
    ) -> bool:
        if obj and obj.publish_status != PublishStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def has_delete_permission(
        self, request: HttpRequest, obj: Optional[PublishableMixin] = None
    ) -> bool:
        if obj and obj.publish_status != PublishStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)
