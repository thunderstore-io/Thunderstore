from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, signals
from django.urls import reverse
from django.utils.functional import cached_property

from thunderstore.cache.cache import CacheBustCondition, invalidate_cache
from thunderstore.core.mixins import TimestampMixin
from thunderstore.repository.models.thread import CommentsThreadMixin


class PackageListingQueryset(models.QuerySet):
    def active(self):
        return self.exclude(package__is_active=False).exclude(
            ~Q(package__versions__is_active=True)
        )


# TODO: Add a db constraint that ensures a package listing and it's categories
#       belong to the same community. This might require actually specifying
#       the intermediate model in code rather than letting Django handle it
class PackageListing(CommentsThreadMixin, TimestampMixin, models.Model):
    """
    Represents a package's relation to how it's displayed on the site and APIs
    """

    objects = PackageListingQueryset.as_manager()

    community = models.ForeignKey(
        "community.Community",
        related_name="package_listings",
        on_delete=models.CASCADE,
    )
    package = models.ForeignKey(
        "repository.Package",
        related_name="community_listings",
        on_delete=models.CASCADE,
    )
    categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="packages",
        blank=True,
    )
    has_nsfw_content = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("package", "community"), name="one_listing_per_community"
            ),
        ]

    def validate(self):
        if self.pk:
            if PackageListing.objects.get(pk=self.pk).community != self.community:
                raise ValidationError("PackageListing.community is read only")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.package.name

    def get_absolute_url(self):
        return reverse(
            "packages.detail",
            kwargs={"owner": self.package.owner.name, "name": self.package.name},
        )

    @cached_property
    def owner_url(self):
        return reverse(
            "packages.list_by_owner", kwargs={"owner": self.package.owner.name}
        )

    @cached_property
    def dependants_url(self):
        return reverse(
            "packages.list_by_dependency",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
            },
        )

    @cached_property
    def rating_score(self):
        annotated = getattr(self, "_rating_score", None)
        if annotated is not None:
            return annotated
        return self.package.rating_score

    @cached_property
    def total_downloads(self):
        annotated = getattr(self, "_total_downloads", None)
        if annotated is not None:
            return annotated
        return self.package.downloads

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)


signals.post_save.connect(PackageListing.post_save, sender=PackageListing)
signals.post_delete.connect(PackageListing.post_delete, sender=PackageListing)
