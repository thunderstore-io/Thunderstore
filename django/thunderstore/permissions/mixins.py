from django.db import models, transaction
from django.db.models import Q

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

    @transaction.atomic
    def update_visibility(self):
        pass

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk and not self.visibility:
            self.visibility = VisibilityFlags.objects.create_unpublished()

        self.update_visibility()

        super().save()

    class Meta:
        abstract = True
