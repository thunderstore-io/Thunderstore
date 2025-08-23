from django.conf import settings
from django.db import models


class UserMeta(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_moderate_any_community = models.BooleanField(default=False)

    @classmethod
    def create_or_update(cls, user):
        from thunderstore.community.models import MODERATION_ROLES, CommunityMembership

        moderation_memberships = CommunityMembership.objects.filter(
            user=user, role__in=MODERATION_ROLES
        )

        can_moderate = moderation_memberships.exists()

        meta, _ = cls.objects.get_or_create(user=user)
        if meta.can_moderate_any_community != can_moderate:
            meta.can_moderate_any_community = can_moderate
            meta.save(update_fields=["can_moderate_any_community"])

        return meta
