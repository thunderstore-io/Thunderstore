from django.core.validators import FileExtensionValidator
from django.db import models

from thunderstore.core.mixins import TimestampMixin


def get_community_filepath(instance, filename):
    return f"community/{instance.community.identifier}/{filename}"


class CommunitySite(TimestampMixin, models.Model):
    site = models.OneToOneField(
        "sites.Site",
        related_name="community",
        on_delete=models.CASCADE,
    )
    community = models.ForeignKey(
        "community.Community",
        related_name="sites",
        on_delete=models.CASCADE,
    )

    slogan = models.CharField(max_length=512, blank=True, null=True)
    description = models.CharField(max_length=512, blank=True, null=True)

    icon = models.ImageField(
        upload_to=get_community_filepath,
        width_field="icon_width",
        height_field="icon_height",
        blank=True,
        null=True,
    )
    icon_width = models.PositiveIntegerField(default=0)
    icon_height = models.PositiveIntegerField(default=0)

    favicon = models.FileField(
        upload_to=get_community_filepath,
        validators=[FileExtensionValidator(allowed_extensions=["ico"])],
        blank=True,
        null=True,
    )

    social_auth_github_key = models.TextField(blank=True, null=True)
    social_auth_github_secret = models.TextField(blank=True, null=True)

    social_auth_discord_key = models.TextField(blank=True, null=True)
    social_auth_discord_secret = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.community)

    def save(self, *args, **kwargs):
        if not self.icon:
            self.icon_width = 0
            self.icon_height = 0
            if "update_fields" in kwargs:
                kwargs["update_fields"] = set(
                    kwargs["update_fields"]
                    + (
                        "icon_width",
                        "icon_height",
                    )
                )
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "community site"
        verbose_name_plural = "community sites"
