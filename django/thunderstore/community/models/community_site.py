from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.functional import cached_property

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

    def __str__(self):
        return str(self.community)

    @property
    def full_url(self) -> str:
        return f"{settings.PROTOCOL}{self.site.domain}/"

    @cached_property
    def get_absolute_url(self):
        return reverse(
            "communities:community:packages.list",
            kwargs={
                "community_identifier": self.community.identifier,
            },
        )

    class Meta:
        verbose_name = "community site"
        verbose_name_plural = "community sites"
