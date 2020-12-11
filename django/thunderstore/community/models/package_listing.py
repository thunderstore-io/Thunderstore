from django.db import models

from thunderstore.core.mixins import TimestampMixin


# TODO: Add a db constraint that ensures a package listing and it's categories
#       belong to the same community. This might require actually specifying
#       the intermediate model in code rather than letting Django handle it
class PackageListing(TimestampMixin, models.Model):
    """
    Represents a package's relation to how it's displayed on the site and APIs
    """

    community = models.ForeignKey(
        "community.Community",
        related_name="package_listings",
        on_delete=models.CASCADE,
    )
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
