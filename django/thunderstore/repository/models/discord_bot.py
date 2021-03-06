from django.conf import settings
from django.db import models


class DiscordUserBotPermission(models.Model):
    thunderstore_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    label = models.CharField(
        max_length=64,
    )
    discord_user_id = models.CharField(
        max_length=64,
    )
    can_deprecate = models.BooleanField(
        default=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("thunderstore_user", "discord_user_id"),
                name="one_permission_per_user",
            ),
        ]
        verbose_name = "Discord User Permissions"
        verbose_name_plural = "Discord User Permissions"
