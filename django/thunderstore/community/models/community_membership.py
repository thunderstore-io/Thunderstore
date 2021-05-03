from django.conf import settings
from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.utils import ChoiceEnum


class CommunityMemberRole(ChoiceEnum):
    owner = "owner"
    moderator = "moderator"
    member = "member"


class CommunityMembership(TimestampMixin, models.Model):
    objects: "Manager[CommunityMembership]"

    community = models.ForeignKey(
        "community.Community",
        related_name="members",
        on_delete=models.CASCADE,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_memberships",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=64,
        default=CommunityMemberRole.member,
        choices=CommunityMemberRole.as_choices(),
    )

    def __str__(self):
        return f"{self.user.username} membership to {self.community.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "community"), name="one_community_membership_per_user"
            ),
        ]
        verbose_name = "community member"
        verbose_name_plural = "community members"
