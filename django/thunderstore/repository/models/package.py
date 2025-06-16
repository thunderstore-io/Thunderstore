import re
import uuid
from distutils.version import StrictVersion
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Case, Q, Sum, When, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache_on_commit_async
from thunderstore.core.enums import OptionalBoolChoice
from thunderstore.core.mixins import AdminLinkMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity
from thunderstore.permissions.mixins import VisibilityMixin
from thunderstore.permissions.models.visibility import VisibilityFlagsQuerySet
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.consts import PACKAGE_NAME_REGEX

if TYPE_CHECKING:
    from thunderstore.repository.models import PackageWiki


class PackageQueryset(VisibilityFlagsQuerySet):
    def active(self):
        return self.exclude(is_active=False).exclude(~Q(versions__is_active=True))


def get_package_dependants(package_pk: int):
    return Package.objects.exclude(
        ~Q(
            versions__dependencies__package=package_pk,
        )
    ).active()


@cache_function_result(CacheBustCondition.any_package_updated)
def get_package_dependants_list(package_pk: int):
    return list(get_package_dependants(package_pk))


class Package(VisibilityMixin, AdminLinkMixin):
    objects = PackageQueryset.as_manager()
    wiki: Optional["PackageWiki"]

    owner = models.ForeignKey(
        "repository.Team",
        on_delete=models.PROTECT,
        related_name="owned_packages",
    )
    namespace = models.ForeignKey(
        "repository.Namespace",
        on_delete=models.PROTECT,
        related_name="packages",
    )
    name = models.CharField(
        max_length=128,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_deprecated = models.BooleanField(
        default=False,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    date_updated = models.DateTimeField(
        auto_now_add=True,
    )
    uuid4 = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    is_pinned = models.BooleanField(
        default=False,
    )
    latest = models.ForeignKey(
        "repository.PackageVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
    )

    show_decompilation_results = models.TextField(
        choices=OptionalBoolChoice.choices,
        default=OptionalBoolChoice.NONE,
    )

    class Meta:
        permissions = (("deprecate_package", "Can manage package deprecation status"),)
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "name"), name="unique_name_per_namespace"
            ),
        ]

    def validate(self):
        if not re.match(PACKAGE_NAME_REGEX, self.name):
            raise ValidationError(
                "Package names can only contain a-z A-Z 0-9 _ characters"
            )

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    def get_or_create_package_listing(self, community):
        from thunderstore.community.models import PackageListing

        listing, _ = PackageListing.objects.get_or_create(
            package=self,
            community=community,
        )
        return listing

    def get_package_listing(self, community):
        from thunderstore.community.models import PackageListing

        return PackageListing.objects.filter(
            package=self,
            community=community,
        ).first()

    def update_listing(self, has_nsfw_content, categories, community):
        listing = self.get_or_create_package_listing(community)
        listing.has_nsfw_content = has_nsfw_content
        if categories:
            listing.categories.add(*categories)
        listing.save(update_fields=("has_nsfw_content",))

    @cached_property
    def has_wiki(self) -> bool:
        try:
            return self.wiki.wiki.pages.exists()
        except ObjectDoesNotExist:
            return False

    @cached_property
    def full_package_name(self):
        return f"{self.owner.name}-{self.name}"

    @cached_property
    def reference(self):
        from thunderstore.repository.package_reference import PackageReference

        return PackageReference(
            namespace=self.owner.name,
            name=self.name,
        )

    @cached_property
    def display_name(self):
        return self.name.replace("_", " ")

    @cached_property
    def available_versions(self):
        # TODO: Caching
        versions = self.versions.filter(is_active=True).values_list(
            "pk", "version_number"
        )
        ordered = sorted(versions, key=lambda version: StrictVersion(version[1]))
        pk_list = [version[0] for version in reversed(ordered)]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_list)])
        return (
            self.versions.filter(pk__in=pk_list)
            .order_by(preserved)
            .prefetch_related(
                "dependencies",
                "dependencies__package",
                "dependencies__package__owner",
            )
            .select_related(
                "package",
                "package__owner",
            )
        )

    @cached_property
    def downloads(self):
        # TODO: Caching
        return self.versions.aggregate(downloads=Sum("downloads"))["downloads"]

    @cached_property
    def rating_score(self):
        return self.package_ratings.count()

    @cached_property
    def icon(self):
        return self.latest.icon

    @cached_property
    def website_url(self):
        return self.latest.website_url

    @cached_property
    def version_number(self):
        return self.latest.version_number

    @cached_property
    def description(self):
        return self.latest.description

    @cached_property
    def dependencies(self):
        return self.latest.dependencies.all()

    @cached_property
    def sorted_dependencies(self):
        return (
            self.latest.dependencies.select_related("package")
            .annotate(total_downloads=Sum("package__versions__downloads"))
            .order_by("-package__is_pinned", "-total_downloads")
        )

    @cached_property
    def is_removed(self):
        return not self.is_effectively_active

    @cached_property
    def is_effectively_active(self):
        return self.is_active and self.versions.filter(is_active=True).count() > 0

    @cached_property
    def dependants_list(self):
        return get_package_dependants_list(self.pk)

    def readme(self):
        return self.latest.readme

    def changelog(self):
        return self.latest.changelog

    def get_absolute_url(self) -> str:
        return reverse(
            "old_urls:packages.detail",
            kwargs={"owner": self.owner.name, "name": self.name},
        )

    def get_view_on_site_url(self) -> Optional[str]:
        # This function is currently only used in Django admin, so it doens't
        # matter too much which community it links to. That said, this should
        # be updated once the concept of a "main page" for a mod exists.
        # TODO: Point this to the main page of a package once that exists as a concept
        from thunderstore.community.models import PackageListing

        listing = PackageListing.objects.active().filter(package=self).first()
        return listing.get_full_url() if listing else None

    def get_page_url(self, community_identifier: str) -> str:
        return reverse(
            "communities:community:packages.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "community_identifier": community_identifier,
            },
        )

    def get_full_url(self, site: Optional[Site] = None):
        hostname = settings.PRIMARY_HOST if site is None else site.domain
        return "%(protocol)s%(hostname)s%(path)s" % {
            "protocol": settings.PROTOCOL,
            "hostname": hostname,
            "path": self.get_absolute_url(),
        }

    def recache_latest(self):
        old_latest = self.latest
        if hasattr(self, "available_versions"):
            del self.available_versions  # Bust the version cache
        self.latest = self.available_versions.first()
        if old_latest != self.latest:
            self.save()

    def handle_created_version(self, version):
        self.date_updated = timezone.now()
        self.is_deprecated = False
        self.save()

    def handle_updated_version(self, version):
        self.recache_latest()

    def handle_deleted_version(self, version):
        self.recache_latest()

    def deprecate(self):
        self.is_deprecated = True
        self.save(update_fields=("is_deprecated",))

    def undeprecate(self):
        self.is_deprecated = False
        self.save(update_fields=("is_deprecated",))

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=("is_active",))

    def ensure_user_can_manage_deprecation(self, user: Optional[UserType]) -> None:
        user = validate_user(user)
        if user.is_staff and (
            user.has_perm("repository.change_package")
            or user.has_perm("repository.deprecate_package")
        ):
            return

        moderated_community_ids = user.moderated_communities

        if moderated_community_ids:
            community_ids = [
                listing.community.id
                for listing in self.community_listings.select_related("community")
            ]

            if community_ids and all(
                str(cid) in moderated_community_ids for cid in community_ids
            ):
                return

        self.owner.ensure_user_can_manage_packages(user)

    def can_user_manage_deprecation(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_manage_deprecation(user))

    def ensure_user_can_manage_wiki(self, user: Optional[UserType]) -> None:
        return self.owner.ensure_user_can_manage_packages(user)

    def can_user_manage_wiki(self, user: Optional[UserType]) -> bool:
        return self.owner.can_user_manage_packages(user)

    def __str__(self):
        return self.full_package_name

    def is_visible_to_user(self, user: Optional[UserType]) -> bool:
        if not self.visibility:
            return False

        if self.visibility.public_detail:
            return True

        if user is None:
            return False

        if self.visibility.owner_detail:
            if self.owner.can_user_access(user):
                return True

        if self.visibility.moderator_detail:
            for listing in self.community_listings.all():
                if listing.community.can_user_manage_packages(user):
                    return True

        if self.visibility.admin_detail:
            if user.is_superuser:
                return True

        return False

    def set_visibility_from_active_status(self):
        if not self.is_active:
            self.visibility.public_detail = False
            self.visibility.public_list = False
            self.visibility.owner_detail = False
            self.visibility.owner_list = False
            self.visibility.moderator_detail = False
            self.visibility.moderator_list = False

    def set_visibility_from_versions(self):
        visibility_fields = [
            "public_detail",
            "public_list",
            "owner_detail",
            "owner_list",
            "moderator_detail",
            "moderator_list",
        ]

        versions = list(
            self.versions.filter(is_active=True).values(
                *[f"visibility__{field}" for field in visibility_fields]
            )
        )

        any_version_visible = {field: False for field in visibility_fields}

        for field in visibility_fields:
            for version in versions:
                if version[f"visibility__{field}"]:
                    any_version_visible[field] = True
                    break

        for field, exists in any_version_visible.items():
            if not exists:
                setattr(self.visibility, field, False)

    @transaction.atomic
    def update_visibility(self):
        original = self.visibility.as_tuple()

        self.set_default_visibility()

        self.set_visibility_from_active_status()

        if self.visibility.as_tuple() != original:
            for version in self.versions.all():
                version.update_visibility()

        # package visibility levels can't be higher than the union of version visibility levels
        self.set_visibility_from_versions()

        if self.visibility.as_tuple() != original:
            self.visibility.save()
            for listing in self.community_listings.all():
                listing.update_visibility()

            self.recache_latest()  # latest available version could potentially change if visibility changes
            # TODO: Available versions should be affected by visibility

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        invalidate_cache_on_commit_async(CacheBustCondition.any_package_updated)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        invalidate_cache_on_commit_async(CacheBustCondition.any_package_updated)


signals.post_save.connect(Package.post_save, sender=Package)
signals.post_delete.connect(Package.post_delete, sender=Package)
