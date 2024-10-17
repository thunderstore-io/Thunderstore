from typing import TYPE_CHECKING, Optional, Tuple

import ulid2
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)
from thunderstore.repository.models import TeamMemberRole

if TYPE_CHECKING:
    from thunderstore.repository.models import Team, TeamMember

User = get_user_model()


class ServiceAccount(models.Model):
    uuid = models.UUIDField(default=ulid2.generate_ulid_as_uuid, primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="service_account",
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        "repository.Team",
        related_name="service_accounts",
        on_delete=models.CASCADE,
    )
    api_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        related_name="created_service_accounts",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    last_used = models.DateTimeField(null=True)

    @classmethod
    @transaction.atomic
    def create(
        cls, owner: "Team", nickname: str, creator: User
    ) -> Tuple["ServiceAccount", str]:
        # All service accounts are bound to a dummy user account.
        service_account_id = ulid2.generate_ulid_as_uuid()
        username = cls.create_username(service_account_id.hex)
        user = User.objects.create_user(
            username,
            email=username,
            first_name=nickname,
        )
        owner.add_member(
            user=user,
            role=TeamMemberRole.member,
        )

        # Force token uniqueness.
        clash = True
        while clash:
            plaintext_token = get_service_account_api_token()
            hashed = hash_service_account_api_token(plaintext_token)
            clash = ServiceAccount.objects.filter(api_token=hashed).exists()

        account = cls.objects.create(
            uuid=service_account_id,
            user=user,
            owner=owner,
            api_token=hashed,
            created_by=creator,
        )

        return (account, plaintext_token)

    @classmethod
    def create_username(cls, id_: str) -> str:
        return f"{id_}.sa@thunderstore.io"

    @property
    def nickname(self) -> str:
        return self.user.first_name

    @property
    def owner_membership(self) -> "Optional[TeamMember]":
        return self.owner.members.filter(user=self.user).first()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        self.user.delete()
        return super().delete(*args, **kwargs)
