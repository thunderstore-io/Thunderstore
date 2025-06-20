from django.conf import settings
from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.utils import ChoiceEnum


class CommunityMemberRole(ChoiceEnum):
    owner = "owner"
    moderator = "moderator"
    janitor = "janitor"
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

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_role = None

        if not is_new:
            old = CommunityMembership.objects.filter(pk=self.pk).only("role").first()
            if old:
                old_role = old.role

        super().save(*args, **kwargs)

        if is_new or (old_role != self.role):
            from thunderstore.account.models import UserMeta

            meta, created = UserMeta.objects.get_or_create(user=self.user)
            if not meta.can_moderate_any_community:
                if self.role in {
                    CommunityMemberRole.moderator,
                    CommunityMemberRole.janitor,
                    CommunityMemberRole.owner,
                }:
                    meta.can_moderate_any_community = True
                    meta.save(update_fields=["can_moderate_any_community"])
