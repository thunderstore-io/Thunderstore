from django.db import models

from thunderstore.core.mixins import TimestampMixin


class PackageListing(TimestampMixin, models.Model):
    """
    Represents a package's relation to how it's displayed on the site and APIs
    """

    package = models.ForeignKey(
        "repository.Package",
        related_name="package_listings",
        on_delete=models.CASCADE
    )
    categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="packages",
        blank=True,
    )
    has_nsfw_content = models.BooleanField(default=False)

    def __str__(self):
        return self.package.name
