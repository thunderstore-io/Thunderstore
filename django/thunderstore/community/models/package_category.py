from django.db import models

from thunderstore.core.mixins import TimestampMixin


class PackageCategoryQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)


class PackageCategoryManager(models.Manager.from_queryset(PackageCategoryQuerySet)):
    pass


class PackageCategory(TimestampMixin, models.Model):
    objects = PackageCategoryManager()
    community = models.ForeignKey(
        "community.Community",
        related_name="package_categories",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=512)
    slug = models.SlugField()
    hidden = models.BooleanField(default=False)

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
