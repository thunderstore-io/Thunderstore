from typing import TYPE_CHECKING, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager, QuerySet
from django.urls import reverse
from django.utils.functional import cached_property

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models.community_membership import (
    CommunityMemberRole,
    CommunityMembership,
)
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity

if TYPE_CHECKING:
    from thunderstore.community.models.community_site import CommunitySite


class CommunityManager(models.Manager):
    def listed(self) -> "QuerySet[Community]":  # TODO: Generic type
        return self.exclude(is_listed=False)


def get_community_filepath(instance: "Community", filename: str) -> str:
    return f"community/{instance.identifier}/{filename}"


class Community(TimestampMixin, models.Model):
    objects: "CommunityManager[Community]" = CommunityManager()
    members: "Manager[CommunityMembership]"

    slogan = models.CharField(max_length=512, blank=True, null=True)
    description = models.CharField(max_length=512, blank=True, null=True)

    icon = models.ImageField(
        upload_to=get_community_filepath,
        width_field="icon_width",
        height_field="icon_height",
        blank=True,
        null=True,
    )
    icon_width = models.PositiveIntegerField(default=0)
    icon_height = models.PositiveIntegerField(default=0)

    background_image = models.ImageField(
        upload_to=get_community_filepath,
        width_field="background_image_width",
        height_field="background_image_height",
        blank=True,
        null=True,
    )
    background_image_width = models.PositiveIntegerField(default=0)
    background_image_height = models.PositiveIntegerField(default=0)

    identifier = models.CharField(max_length=256, unique=True, db_index=True)
    name = models.CharField(max_length=256)
    discord_url = models.CharField(max_length=512, blank=True, null=True)
    wiki_url = models.CharField(max_length=512, blank=True, null=True)
    is_listed = models.BooleanField(default=True)
    require_package_listing_approval = models.BooleanField(default=False)
    block_auto_updates = models.BooleanField(default=True)

    @property
    def total_package_count(self) -> int:
        # TODO: Implement as a cached value with background updates
        return -1

    @property
    def total_download_count(self) -> int:
        # TODO: Implement as a cached value with background updates
        return -1

    def save(self, *args, **kwargs):
        if self.pk:
            in_db = type(self).objects.get(pk=self.pk)
            if in_db.identifier != self.identifier:
                raise ValidationError("Field 'identifier' is read only")
        if not self.icon:
            self.icon_width = 0
            self.icon_height = 0
            if "update_fields" in kwargs:
                kwargs["update_fields"] = set(
                    kwargs["update_fields"]
                    + (
                        "icon_width",
                        "icon_height",
                    )
                )
        if not self.background_image:
            self.background_image_width = 0
            self.background_image_height = 0
            if "update_fields" in kwargs:
                kwargs["update_fields"] = set(
                    kwargs["update_fields"]
                    + (
                        "background_image_width",
                        "background_image_height",
                    )
                )
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "community"
        verbose_name_plural = "communities"

    def get_membership_for_user(self, user) -> Optional[CommunityMembership]:
        if not hasattr(self, "__membership_cache"):
            self.__membership_cache = {}
        if user.pk not in self.__membership_cache:
            self.__membership_cache[user.pk] = self.members.filter(user=user).first()
        return self.__membership_cache[user.pk]

    @cached_property
    def background_image_url(self) -> Optional[str]:
        """
        Return URL to the community's background image if one exists.
        """
        return None if not bool(self.background_image) else self.background_image.url

    def ensure_user_can_manage_packages(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if hasattr(user, "service_account"):
            raise ValidationError("Service accounts are unable to manage packages")
        membership = self.get_membership_for_user(user)
        if (
            not membership
            or membership.role
            not in (
                CommunityMemberRole.moderator,
                CommunityMemberRole.owner,
            )
        ) and not (
            user.is_superuser or user.is_staff
        ):  # TODO: Maybe remove
            raise ValidationError("Must be a moderator or higher to manage packages")

    def can_user_manage_packages(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_manage_packages(user))

    @staticmethod
    def should_use_old_urls(instance: Optional["Community"]) -> bool:
        return not instance or bool(instance.main_site)

    @cached_property
    def main_site(self) -> Optional["CommunitySite"]:
        return self.sites.first()

    @property
    def full_url(self):
        return (
            self.main_site.full_url
            if Community.should_use_old_urls(self)
            else reverse(
                "communities:community:packages.list",
                kwargs={
                    "community_identifier": self.identifier,
                },
            )
        )

    @property
    def valid_review_statuses(self):
        if self.require_package_listing_approval:
            return (PackageListingReviewStatus.approved,)
        return (
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.unreviewed,
        )
