from typing import TYPE_CHECKING, Optional

import ulid2
from django.conf import settings
from django.db import models, transaction

if TYPE_CHECKING:
    from thunderstore.repository.models import UploaderIdentityMember


class ServiceAccount(models.Model):
    uuid = models.UUIDField(default=ulid2.generate_ulid_as_uuid, primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="service_account",
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        "repository.UploaderIdentity",
        related_name="service_accounts",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True)

    @property
    def nickname(self) -> str:
        return self.user.first_name

    @property
    def owner_membership(self) -> "Optional[UploaderIdentityMember]":
        return self.owner.members.filter(user=self.user).first()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        self.user.delete()
        return super().delete(*args, **kwargs)
