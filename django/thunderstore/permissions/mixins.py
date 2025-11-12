from abc import abstractmethod
from typing import Optional

from django.db import models, transaction
from django.db.models import Q

from thunderstore.core.types import UserType
from thunderstore.core.utils import extend_update_fields_if_present
from thunderstore.permissions.models import VisibilityFlags


class VisibilityQuerySet(models.QuerySet):
    def public_list(self):
        return self.exclude(visibility__public_list=False)

    def public_detail(self):
        return self.exclude(visibility__public_detail=False)

    def visible_list(self, is_owner: bool, is_moderator: bool, is_admin: bool):
        filter = Q(visibility__public_list=True)
        if is_owner:
            filter |= Q(visibility__owner_list=True)
        if is_moderator:
            filter |= Q(visibility__moderator_list=True)
        if is_admin:
            filter |= Q(visibility__admin_list=True)
        return self.exclude(~filter)

    def visible_detail(self, is_owner: bool, is_moderator: bool, is_admin: bool):
        filter = Q(visibility__public_detail=True)
        if is_owner:
            filter |= Q(visibility__owner_detail=True)
        if is_moderator:
            filter |= Q(visibility__moderator_detail=True)
        if is_admin:
            filter |= Q(visibility__admin_detail=True)
        return self.exclude(~filter)


class VisibilityMixin(models.Model):
    objects = VisibilityQuerySet.as_manager()
    visibility = models.OneToOneField(
        "permissions.VisibilityFlags",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )

    @abstractmethod
    @transaction.atomic
    def update_visibility(self):  # pragma: no cover
        pass

    def set_default_visibility(self):
        self.visibility.public_detail = True
        self.visibility.public_list = True
        self.visibility.owner_detail = True
        self.visibility.owner_list = True
        self.visibility.moderator_detail = True
        self.visibility.moderator_list = True
        self.visibility.admin_detail = True
        self.visibility.admin_list = True

    def set_zero_visibility(self):
        self.visibility.public_detail = False
        self.visibility.public_list = False
        self.visibility.owner_detail = False
        self.visibility.owner_list = False
        self.visibility.moderator_detail = False
        self.visibility.moderator_list = False
        self.visibility.admin_detail = False
        self.visibility.admin_list = False

    @transaction.atomic
    def save(self, **kwargs):
        if not self.pk and not self.visibility:
            self.visibility = VisibilityFlags.objects.create_public()
            kwargs = extend_update_fields_if_present(kwargs, "visibility")

        self.update_visibility()

        super().save(**kwargs)

    class Meta:
        abstract = True

    @abstractmethod
    def is_visible_to_user(self, user: Optional[UserType]) -> bool:  # pragma: no cover
        return False
