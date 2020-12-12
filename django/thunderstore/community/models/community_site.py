from django.db import models

from thunderstore.core.mixins import TimestampMixin


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

    def __str__(self):
        return str(self.community)

    class Meta:
        verbose_name = "community site"
        verbose_name_plural = "community sites"
