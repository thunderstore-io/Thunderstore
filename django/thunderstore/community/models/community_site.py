from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import QuerySet

from thunderstore.core.mixins import TimestampMixin


class CommunitySiteManager(models.Manager):
    def listed(self) -> "QuerySet[CommunitySiteManager]":  # TODO: Generic type
        return self.exclude(is_listed=False)


def get_community_filepath(instance, filename):
    return f"community/{instance.community.identifier}/{filename}"


class CommunitySite(TimestampMixin, models.Model):
    objects: "CommunitySiteManager[CommunitySite]" = CommunitySiteManager()

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
    is_listed = models.BooleanField(default=True)

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

    background_image = models.ImageField(
        upload_to=get_community_filepath,
        width_field="background_image_width",
        height_field="background_image_height",
        blank=True,
        null=True,
    )
    background_image_width = models.PositiveIntegerField(default=0)
    background_image_height = models.PositiveIntegerField(default=0)

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
        if not self.background_image:
            self.background_image_width = 0
            self.background_image_height = 0
            if "update_fields" in kwargs:
                kwargs["update_fields"] = set(
                    kwargs["update_fields"]
                    + (
                        "background_image_width",
                        "background_image_height",
                    )
                )
        return super().save(*args, **kwargs)

    @property
    def full_url(self) -> str:
        return f"{settings.PROTOCOL}{self.site.domain}/"

    class Meta:
        verbose_name = "community site"
        verbose_name_plural = "community sites"
