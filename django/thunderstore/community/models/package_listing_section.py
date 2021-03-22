import ulid2
from django.db import models

from thunderstore.core.mixins import TimestampMixin


class PackageListingSectionQueryset(models.QuerySet):
    def listed(self) -> "PackageListingSectionQueryset":
        return self.exclude(is_listed=False)


class PackageListingSection(TimestampMixin, models.Model):
    objects = PackageListingSectionQueryset.as_manager()

    uuid = models.UUIDField(
        default=ulid2.generate_ulid_as_uuid,
        primary_key=True,
        editable=False,
    )
    community = models.ForeignKey(
        "community.Community",
        on_delete=models.CASCADE,
        related_name="package_listing_sections",
    )

    name = models.CharField(
        max_length=256,
        help_text="Name of the section, for display purposes only",
    )
    slug = models.SlugField()
    is_listed = models.BooleanField(default=True)

    priority = models.IntegerField(
        default=0,
        help_text=(
            "Priority of the section. "
            "Highest priority section will be shown by default."
        ),
    )

    require_categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="required_on_package_listing_filters",
        blank=True,
    )
    exclude_categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="excluded_on_package_listing_filters",
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("community", "slug"), name="unique_slug_per_community"
            ),
        ]

    def __str__(self):
        return f"{self.community.name} -> {self.name}"
