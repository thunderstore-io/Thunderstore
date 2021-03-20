from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin


class PackageCategory(TimestampMixin, models.Model):
    objects: "Manager[PackageCategory]"
    community = models.ForeignKey(
        "community.Community",
        related_name="package_categories",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=512)
    slug = models.SlugField()

    def __str__(self):
        return f"{self.community.name} -> {self.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("slug", "community"), name="unique_category_slug_per_community"
            ),
        ]
        verbose_name = "package category"
        verbose_name_plural = "package categories"
