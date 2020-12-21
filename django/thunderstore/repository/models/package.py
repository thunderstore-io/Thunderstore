import re
import uuid
from distutils.version import StrictVersion

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, Q, Sum, When, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from thunderstore.core.cache import CacheBustCondition, invalidate_cache
from thunderstore.repository.consts import PACKAGE_NAME_REGEX


class PackageQueryset(models.QuerySet):
    def active(self):
        return self.exclude(is_active=False).exclude(~Q(versions__is_active=True))


class Package(models.Model):
    objects = PackageQueryset.as_manager()
    owner = models.ForeignKey(
        "repository.UploaderIdentity",
        on_delete=models.PROTECT,
        related_name="owned_packages",
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

    class Meta:
        unique_together = ("owner", "name")

    def validate(self):
        if not re.match(PACKAGE_NAME_REGEX, self.name):
            raise ValidationError(
                "Package names can only contain a-Z A-Z 0-9 _ characers"
            )

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    def get_package_listing(self, community):
        from thunderstore.community.models import PackageListing

        listing, _ = PackageListing.objects.get_or_create(
            package=self,
            community=community,
        )
        return listing

    def update_listing(self, has_nsfw_content, categories, community):
        listing = self.get_package_listing(community)
        listing.has_nsfw_content = has_nsfw_content
        if categories:
            listing.categories.set(categories)
        listing.save(update_fields=("has_nsfw_content",))

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
        return self.latest.display_name

    @cached_property
    def license(self):
        return self.latest.license

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
    def is_effectively_active(self):
        return self.is_active and self.versions.filter(is_active=True).count() > 0

    @cached_property
    def dependants(self):
        # TODO: Caching
        return Package.objects.exclude(
            ~Q(
                versions__dependencies__package=self,
            )
        ).active()

    @cached_property
    def owner_url(self):
        return reverse("packages.list_by_owner", kwargs={"owner": self.owner.name})

    @cached_property
    def dependants_url(self):
        return reverse(
            "packages.list_by_dependency",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
            },
        )

    @cached_property
    def readme(self):
        return self.latest.readme

    def get_absolute_url(self):
        return reverse(
            "packages.detail", kwargs={"owner": self.owner.name, "name": self.name}
        )

    def get_full_url(self, site: Site):
        return "%(protocol)s%(hostname)s%(path)s" % {
            "protocol": settings.PROTOCOL,
            "hostname": site.domain,
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

    def __str__(self):
        return self.full_package_name

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)


signals.post_save.connect(Package.post_save, sender=Package)
signals.post_delete.connect(Package.post_delete, sender=Package)
