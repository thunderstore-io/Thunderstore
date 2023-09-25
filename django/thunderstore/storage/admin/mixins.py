from typing import Optional

from django.db.models import Model
from django.http import HttpRequest


class ReadOnlyInline:
    extra = 0

    def has_add_permission(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> bool:
        return False
