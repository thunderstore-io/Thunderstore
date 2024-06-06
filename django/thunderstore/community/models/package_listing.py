from typing import TYPE_CHECKING, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache_on_commit_async
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.core.mixins import AdminLinkMixin, TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.permissions.utils import validate_user
from thunderstore.webhooks.audit import (
    AuditAction,
    AuditEvent,
    AuditEventField,
    fire_audit_event,
)

if TYPE_CHECKING:
    from thunderstore.community.models import PackageCategory


class PackageListingQueryset(models.QuerySet):
    def active(self):
        return self.exclude(package__is_active=False).exclude(
            ~Q(package__versions__is_active=True)
        )

    def approved(self):
        return self.exclude(~Q(review_status=PackageListingReviewStatus.approved))

    def filter_by_community_approval_rule(self):
        return self.exclude(review_status=PackageListingReviewStatus.rejected).exclude(
            Q(community__require_package_listing_approval=True)
            & ~Q(review_status=PackageListingReviewStatus.approved),
        )


# TODO: Add a db constraint that ensures a package listing and it's categories
#       belong to the same community. This might require actually specifying
#       the intermediate model in code rather than letting Django handle it
class PackageListing(TimestampMixin, AdminLinkMixin, models.Model):
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
    is_review_requested = models.BooleanField(
        default=False,
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
    is_auto_imported = models.BooleanField(default=False)

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
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.detail",
                kwargs={"owner": self.package.owner.name, "name": self.package.name},
            )
        )

    def get_wiki_url(self) -> str:
        return reverse(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.detail.wiki",
                kwargs={"owner": self.package.owner.name, "name": self.package.name},
            )
        )

    def get_versions_url(self) -> str:
        return reverse(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.detail.versions",
                kwargs={"owner": self.package.owner.name, "name": self.package.name},
            )
        )

    def get_changelog_url(self) -> str:
        return reverse(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.detail.changelog",
                kwargs={"owner": self.package.owner.name, "name": self.package.name},
            )
        )

    def get_full_url(self):
        hostname = (
            settings.PRIMARY_HOST
            if (site := self.community.main_site) is None
            else site.site.domain
        )
        return "%(protocol)s%(hostname)s%(path)s" % {
            "protocol": settings.PROTOCOL,
            "hostname": hostname,
            "path": self.get_absolute_url(),
        }

    def build_audit_event(
        self,
        *,
        action: AuditAction,
        user_id: Optional[int],
        message: Optional[str] = None,
    ) -> AuditEvent:
        return AuditEvent(
            timestamp=timezone.now(),
            user_id=user_id,
            community_id=self.community.pk,
            action=action,
            message=message,
            related_url=self.get_full_url(),
            fields=[
                AuditEventField(
                    name="Community",
                    value=self.community.name,
                ),
                AuditEventField(
                    name="Package",
                    value=self.package.full_package_name,
                ),
            ],
        )

    @transaction.atomic
    def request_review(self):
        self.is_review_requested = True
        self.save(update_fields=("is_review_requested",))

    @transaction.atomic
    def clear_review_request(self):
        self.is_review_requested = False
        self.save(update_fields=("is_review_requested",))

    @transaction.atomic
    def reject(
        self,
        agent: Optional[UserType],
        rejection_reason: str,
        is_system: bool = False,
        internal_notes: Optional[str] = None,
    ):
        if is_system or self.can_user_manage_approval_status(agent):
            self.rejection_reason = rejection_reason
            self.review_status = PackageListingReviewStatus.rejected
            self.notes = internal_notes or self.notes
            self.save(
                update_fields=(
                    "rejection_reason",
                    "review_status",
                    "notes",
                )
            )
            message = "\n\n".join(filter(bool, (rejection_reason, internal_notes)))
            fire_audit_event(
                self.build_audit_event(
                    action=AuditAction.PACKAGE_REJECTED,
                    user_id=agent.pk if agent else None,
                    message=message,
                )
            )
        else:
            raise PermissionError()

    @transaction.atomic
    def approve(
        self,
        agent: Optional[UserType],
        is_system: bool = False,
        internal_notes: Optional[str] = None,
    ):
        if is_system or self.can_user_manage_approval_status(agent):
            self.review_status = PackageListingReviewStatus.approved
            self.notes = internal_notes or self.notes
            self.save(
                update_fields=(
                    "review_status",
                    "notes",
                )
            )
            fire_audit_event(
                self.build_audit_event(
                    action=AuditAction.PACKAGE_APPROVED,
                    user_id=agent.pk if agent else None,
                    message=internal_notes,
                )
            )
        else:
            raise PermissionError()

    @cached_property
    def owner_url(self):
        return reverse(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.list_by_owner",
                kwargs={"owner": self.package.owner.name},
            )
        )

    @cached_property
    def dependants_url(self):
        return reverse(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.list_by_dependency",
                kwargs={
                    "owner": self.package.owner.name,
                    "name": self.package.name,
                },
            )
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

    def can_be_moderated_by_user(self, user: Optional[UserType]) -> bool:
        return self.community.can_user_manage_packages(user)

    def ensure_user_can_manage_listing(self, user: Optional[UserType]) -> None:
        user = validate_user(user)
        is_allowed = self.can_be_moderated_by_user(
            user
        ) or self.package.owner.can_user_manage_packages(user)
        if not is_allowed:
            raise ValidationError("Must have listing management permission")

    def ensure_update_categories_permission(self, user: Optional[UserType]) -> None:
        self.ensure_user_can_manage_listing(user)

    def check_update_categories_permission(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_update_categories_permission(user))

    def can_user_manage_approval_status(self, user: Optional[UserType]) -> bool:
        return self.can_be_moderated_by_user(user)

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
