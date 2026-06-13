from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Manager, QuerySet
from django.urls import reverse
from django.utils.functional import cached_property

from django_extrafields.models import SafeOneToOneOrField
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models.community_membership import (
    CommunityMemberRole,
    CommunityMembership,
)
from thunderstore.core.enums import OptionalBoolChoice
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity, extend_update_fields_if_present
from thunderstore.permissions.utils import validate_user

if TYPE_CHECKING:
    from thunderstore.community.models.community_site import CommunitySite


class CommunityManager(models.Manager):
    def get_queryset(self):
        # Always join aggregated fields when creating a QuerySet.
        return super().get_queryset().select_related("aggregated_fields")

    def listed(self) -> "QuerySet[Community]":  # TODO: Generic type
        return self.exclude(is_listed=False)


def get_community_filepath(instance: "Community", filename: str) -> str:
    return f"community/{instance.identifier}/{filename}"


class Community(TimestampMixin, models.Model):
    objects: "CommunityManager[Community]" = CommunityManager()
    members: "Manager[CommunityMembership]"

    aggregated_fields = SafeOneToOneOrField(
        "CommunityAggregatedFields",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    slogan = models.CharField(max_length=512, blank=True, null=True)
    short_description = models.CharField(max_length=512, blank=True, null=True)
    description = models.CharField(max_length=512, blank=True, null=True)

    # These require COMMUNITY_IMAGE_HOST to be set in the .env to function
    icon_path = models.CharField(max_length=512, blank=True, null=True)
    community_icon_path = models.CharField(max_length=512, blank=True, null=True)
    cover_image_path = models.CharField(max_length=512, blank=True, null=True)
    background_image_path = models.CharField(max_length=512, blank=True, null=True)
    hero_image_path = models.CharField(max_length=512, blank=True, null=True)

    icon = models.ImageField(
        upload_to=get_community_filepath,
        width_field="icon_width",
        height_field="icon_height",
        blank=True,
        null=True,
    )
    icon_width = models.PositiveIntegerField(default=0)
    icon_height = models.PositiveIntegerField(default=0)

    community_icon = models.ImageField(
        upload_to=get_community_filepath,
        width_field="community_icon_width",
        height_field="community_icon_height",
        blank=True,
        null=True,
    )
    community_icon_width = models.PositiveIntegerField(default=0)
    community_icon_height = models.PositiveIntegerField(default=0)

    cover_image = models.ImageField(
        upload_to=get_community_filepath,
        width_field="cover_image_width",
        height_field="cover_image_height",
        blank=True,
        null=True,
    )
    cover_image_width = models.PositiveIntegerField(default=0)
    cover_image_height = models.PositiveIntegerField(default=0)

    background_image = models.ImageField(
        upload_to=get_community_filepath,
        width_field="background_image_width",
        height_field="background_image_height",
        blank=True,
        null=True,
    )
    background_image_width = models.PositiveIntegerField(default=0)
    background_image_height = models.PositiveIntegerField(default=0)

    hero_image = models.ImageField(
        upload_to=get_community_filepath,
        width_field="hero_image_width",
        height_field="hero_image_height",
        blank=True,
        null=True,
    )
    hero_image_width = models.PositiveIntegerField(default=0)
    hero_image_height = models.PositiveIntegerField(default=0)

    identifier = models.CharField(max_length=256, unique=True, db_index=True)
    name = models.CharField(max_length=256)
    discord_url = models.CharField(max_length=512, blank=True, null=True)
    wiki_url = models.CharField(max_length=512, blank=True, null=True)
    is_listed = models.BooleanField(default=True)
    require_package_listing_approval = models.BooleanField(default=False)
    block_auto_updates = models.BooleanField(default=True)

    show_decompilation_results = models.TextField(
        choices=OptionalBoolChoice.choices,
        default=OptionalBoolChoice.NONE,
    )

    # Will hide/show "Install with Mod Manager" button on package pages
    has_mod_manager_support = models.BooleanField(default=True)

    search_keywords = ArrayField(
        models.CharField(max_length=512),
        blank=True,
        null=True,
        default=list,
    )

    @property
    def aggregated(self) -> "AggregatedFields":
        return (
            self.aggregated_fields.as_class()
            if self.aggregated_fields
            else CommunityAggregatedFields.get_empty()
        )

    def save(self, **kwargs):
        if self.pk:
            in_db = type(self).objects.get(pk=self.pk)
            if in_db.identifier != self.identifier:
                raise ValidationError("Field 'identifier' is read only")
        if not self.icon:
            self.icon_width = 0
            self.icon_height = 0
            kwargs = extend_update_fields_if_present(
                kwargs,
                "icon_width",
                "icon_height",
            )
        if not self.background_image:
            self.background_image_width = 0
            self.background_image_height = 0
            kwargs = extend_update_fields_if_present(
                kwargs,
                "background_image_width",
                "background_image_height",
            )
        if not self.hero_image:
            self.hero_image_width = 0
            self.hero_image_height = 0
            kwargs = extend_update_fields_if_present(
                kwargs,
                "hero_image_width",
                "hero_image_height",
            )
        if not self.cover_image:
            self.cover_image_width = 0
            self.cover_image_height = 0
            kwargs = extend_update_fields_if_present(
                kwargs,
                "cover_image_width",
                "cover_image_height",
            )
        if not self.community_icon:
            self.community_icon_width = 0
            self.community_icon_height = 0
            kwargs = extend_update_fields_if_present(
                kwargs,
                "community_icon_width",
                "community_icon_height",
            )
        return super().save(**kwargs)

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

    def _get_effective_url(
        self, path_field: Optional[str], image_field: models.ImageField
    ) -> Optional[str]:
        """
        If we have a COMMUNITY_IMAGE_HOST and image path, use it, otherwise fallback to legacy image fields
        """
        host = getattr(settings, "COMMUNITY_IMAGE_HOST", None)

        if host and path_field:
            return f"{host.rstrip('/')}/{path_field.lstrip('/')}"

        return image_field.url if image_field else None

    @cached_property
    def background_image_url(self) -> Optional[str]:
        return self._get_effective_url(
            self.background_image_path, self.background_image
        )

    @cached_property
    def hero_image_url(self) -> Optional[str]:
        return self._get_effective_url(self.hero_image_path, self.hero_image)

    @cached_property
    def cover_image_url(self) -> Optional[str]:
        return self._get_effective_url(self.cover_image_path, self.cover_image)

    @cached_property
    def community_icon_url(self) -> Optional[str]:
        return self._get_effective_url(self.community_icon_path, self.community_icon)

    @cached_property
    def icon_url(self) -> Optional[str]:
        return self._get_effective_url(self.icon_path, self.icon)

    def ensure_user_can_moderate_packages(self, user: Optional[UserType]) -> None:
        user = validate_user(user)
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
            raise PermissionValidationError(
                "Must be a moderator or higher to manage packages"
            )

    def ensure_user_can_manage_categories(self, user: Optional[UserType]) -> None:
        user = validate_user(user)
        membership = self.get_membership_for_user(user)

        allowed_roles = [
            CommunityMemberRole.janitor,
            CommunityMemberRole.moderator,
            CommunityMemberRole.owner,
        ]

        if (not membership or membership.role not in allowed_roles) and not (
            user.is_superuser or user.is_staff
        ):  # TODO: Maybe remove
            raise PermissionValidationError(
                "Must be a janitor or higher to manage categories"
            )

    def can_user_manage_packages(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_moderate_packages(user))

    def can_user_manage_categories(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_manage_categories(user))

    @staticmethod
    def should_use_old_urls(instance: Optional["Community"]) -> bool:
        return not instance or bool(instance.main_site)

    @cached_property
    def main_site(self) -> Optional["CommunitySite"]:
        # Prefer the site on PRIMARY_HOST (the canonical main domain) so absolute
        # URLs built from main_site (the v1 API `package_url`, full_url, …) don't
        # drift to a secondary host like the legacy `old.` mirror. Reuse the
        # prefetched `sites` when available (CommunityMixin prefetches them with
        # select_related("site")); otherwise issue a single select_related query
        # so the domain comparison below doesn't trigger an N+1 on
        # community_site.site.
        if "sites" in getattr(self, "_prefetched_objects_cache", {}):
            sites = list(self.sites.all())
        else:
            sites = list(self.sites.select_related("site"))
        if not sites:
            return None
        # CommunitySite has no Meta.ordering, so sort the already-materialized
        # list by pk (no extra query, and it works for the prefetched case too)
        # to keep the fallback below deterministic instead of dependent on DB
        # row order when no site matches PRIMARY_HOST.
        sites.sort(key=lambda community_site: community_site.pk)
        for community_site in sites:
            if community_site.site.domain == settings.PRIMARY_HOST:
                return community_site
        return sites[0]

    def get_absolute_url(self) -> str:
        # Host-relative URL for in-site navigation, so links rendered on the
        # legacy site stay on the host that served the page instead of jumping
        # to the community's main_site (the new app) host.
        #
        # Unlike PackageListing.get_absolute_url(), this deliberately does NOT go
        # through get_community_url_reverse_args() and always uses the explicit
        # `/c/<id>/` scheme. Community links are cross-community (community tiles,
        # the popular-communities nav), so the target usually isn't the community
        # implied by the current host. The implicit `old_urls:` scheme carries no
        # community identifier (old_urls:packages.list -> /package/), so routing
        # through the helper would resolve every link to the serving host's own
        # community. The explicit route is registered on every host, so it also
        # resolves on the legacy site.
        return reverse(
            "communities:community:packages.list",
            kwargs={
                "community_identifier": self.identifier,
            },
        )

    @property
    def full_url(self):
        return (
            self.main_site.full_url
            if Community.should_use_old_urls(self)
            else self.get_absolute_url()
        )

    @property
    def valid_review_statuses(self):
        if self.require_package_listing_approval:
            return (PackageListingReviewStatus.approved,)
        return (
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.unreviewed,
        )


@dataclass
class AggregatedFields:
    download_count: int = 0
    package_count: int = 0


class CommunityAggregatedFields(TimestampMixin, models.Model):
    """
    Computationally heavy fields updated by a periodic background task.
    """

    download_count = models.PositiveIntegerField(default=0)
    package_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.as_class())

    @classmethod
    def get_empty(cls) -> AggregatedFields:
        return AggregatedFields()

    def as_class(self) -> AggregatedFields:
        """
        Return fields in a format supporting attribute access.
        """
        return AggregatedFields(self.download_count, self.package_count)

    @classmethod
    @transaction.atomic
    def create_missing(cls) -> None:
        """
        Create CommunityAggregatedFields objects for Communities that
        don't have none.
        """
        communities = Community.objects.filter(aggregated_fields=None).order_by("pk")

        created_afs = cls.objects.bulk_create(
            [cls() for _ in range(communities.count())],
        )

        for community, aggregated_fields in zip(communities, created_afs):
            community.aggregated_fields = aggregated_fields

        Community.objects.bulk_update(communities, ["aggregated_fields"])

    @classmethod
    def update_for_community(cls, community: Community) -> None:
        """
        Updates field values for given Community.

        Assumes the CommunityAggregatedFields objects has been created
        previously, e.g. by calling .create_missing()
        """
        listings = community.package_listings.active()

        if community.require_package_listing_approval:
            listings = listings.approved()

        # Exclude listings that are shared with other communities
        listings = listings.filter_with_single_community()

        community.aggregated_fields.package_count = listings.count()
        community.aggregated_fields.download_count = sum(
            listing.total_downloads for listing in listings
        )
        community.aggregated_fields.save()
