from typing import TYPE_CHECKING, List, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, signals
from django.urls import reverse
from django.utils.functional import cached_property

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache_on_commit_async
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity

if TYPE_CHECKING:
    from thunderstore.community.models import PackageCategory


class PackageListingQueryset(models.QuerySet):
    def active(self):
        return self.exclude(package__is_active=False).exclude(
            ~Q(package__versions__is_active=True)
        )

    def approved(self):
        return self.exclude(~Q(review_status=PackageListingReviewStatus.approved))


# TODO: Add a db constraint that ensures a package listing and it's categories
#       belong to the same community. This might require actually specifying
#       the intermediate model in code rather than letting Django handle it
class PackageListing(TimestampMixin, models.Model):
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
    review_status = models.CharField(
        default=PackageListingReviewStatus.unreviewed,
        choices=PackageListingReviewStatus.as_choices(),
        max_length=512,
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
    )
    notes = models.TextField(
        null=True,
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

    # TODO: Remove in the end of TS-272
    def get_absolute_url(self):
        return reverse(
            "old_urls:packages.detail",
            kwargs={"owner": self.package.owner.name, "name": self.package.name},
        )

    @cached_property
    def get_absolute_url_with_community_identifier(self):
        return reverse(
            "communities:community:packages.detail",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
                "community_identifier": self.community.identifier,
            },
        )

    # TODO: Remove in the end of TS-272
    @cached_property
    def owner_url(self):
        return reverse(
            "old_urls:packages.list_by_owner", kwargs={"owner": self.package.owner.name}
        )

    @cached_property
    def owner_url_with_community_identifier(self):
        return reverse(
            "communities:community:packages.list_by_owner",
            kwargs={
                "owner": self.package.owner.name,
                "community_identifier": self.community.identifier,
            },
        )

    # TODO: Remove in the end of TS-272
    @cached_property
    def dependants_url(self):
        return reverse(
            "old_urls:packages.list_by_dependency",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
            },
        )

    @cached_property
    def dependants_url_with_community_identifier(self):
        return reverse(
            "communities:community:packages.list_by_dependency",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
                "community_identifier": self.community.identifier,
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
        invalidate_cache_on_commit_async(CacheBustCondition.any_package_updated)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        invalidate_cache_on_commit_async(CacheBustCondition.any_package_updated)

    @property
    def is_waiting_for_approval(self):
        return (
            self.community.require_package_listing_approval
            and self.review_status == PackageListingReviewStatus.unreviewed
        )

    @property
    def is_rejected(self):
        return self.review_status == PackageListingReviewStatus.rejected

    def update_categories(self, agent: UserType, categories: List["PackageCategory"]):
        self.ensure_update_categories_permission(agent)
        for category in categories:
            if category.community_id != self.community_id:
                raise ValidationError(
                    "Community mismatch between package listing and category"
                )
        self.categories.set(categories)

    def ensure_update_categories_permission(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if hasattr(user, "service_account"):
            raise ValidationError("Service accounts are unable to perform this action")
        is_allowed = self.community.can_user_manage_packages(
            user
        ) or self.package.owner.can_user_manage_packages(user)
        if not is_allowed:
            raise ValidationError("Must have package management permission")

    def check_update_categories_permission(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_update_categories_permission(user))

    def ensure_can_be_viewed_by_user(self, user: Optional[UserType]) -> None:
        def get_has_perms() -> bool:
            return (
                user is not None
                and user.is_authenticated
                and (
                    self.community.can_user_manage_packages(user)
                    or self.package.owner.can_user_access(user)
                )
            )

        if self.community.require_package_listing_approval:
            if (
                self.review_status != PackageListingReviewStatus.approved
                and not get_has_perms()
            ):
                raise ValidationError("Insufficient permissions to view")
        else:
            if (
                self.review_status == PackageListingReviewStatus.rejected
                and not get_has_perms()
            ):
                raise ValidationError("Insufficient permissions to view")

    def can_be_viewed_by_user(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_be_viewed_by_user(user))


signals.post_save.connect(PackageListing.post_save, sender=PackageListing)
signals.post_delete.connect(PackageListing.post_delete, sender=PackageListing)
