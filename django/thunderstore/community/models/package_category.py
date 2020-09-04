from django.db import models

from thunderstore.core.mixins import TimestampMixin


class PackageCategory(TimestampMixin, models.Model):
    name = models.CharField(max_length=512)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "package category"
        verbose_name_plural = "package categories"
