import uuid

from datetime import timedelta
from distutils.version import StrictVersion

from ipware import get_client_ip

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.db import models, transaction
from django.db.models import Case, When, Sum, Q, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from core.cache import CacheBustCondition, invalidate_cache
from core.utils import ChoiceEnum

from webhooks.models import Webhook, WebhookType


class UploaderIdentityMemberRole(ChoiceEnum):
    owner = "owner"
    member = "member"


class UploaderIdentityMember(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="author_identities",
        on_delete=models.CASCADE,
    )
    identity = models.ForeignKey(
        "repository.UploaderIdentity",
        related_name="members",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=64,
        default=UploaderIdentityMemberRole.member,
        choices=UploaderIdentityMemberRole.as_choices(),
    )

    class Meta:
        unique_together = ("user", "identity")
        verbose_name = "Uploader Identity Member"
        verbose_name_plural = "Uploader Identy Members"

    def __str__(self):
        return f"{self.user.username} membership to {self.identity.name}"


class UploaderIdentity(models.Model):
    name = models.CharField(
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = "Uploader Identity"
        verbose_name_plural = "Uploader Identities"

    def __str__(self):
        return self.name

    @classmethod
    @transaction.atomic
    def get_or_create_for_user(cls, user):
        identity_membership = user.author_identities.first()
        if identity_membership:
            return identity_membership.identity

        identity, created = cls.objects.get_or_create(
            name=user.username,
        )
        if created:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=identity,
                role=UploaderIdentityMemberRole.owner,
            )
        assert identity.members.filter(user=user).exists()
        return identity


class PackageQueryset(models.QuerySet):
    def active(self):
        return (
            self
            .exclude(is_active=False)
            .exclude(~Q(versions__is_active=True))
        )


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

    @property
    def full_package_name(self):
        return f"{self.owner.name}-{self.name}"

    @property
    def display_name(self):
        return self.name.replace("_", " ")

    @cached_property
    def available_versions(self):
        # TODO: Caching
        versions = self.versions.filter(is_active=True).values_list("pk", "version_number")
        ordered = sorted(versions, key=lambda version: StrictVersion(version[1]))
        pk_list = [version[0] for version in reversed(ordered)]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_list)])
        return self.versions.filter(pk__in=pk_list).order_by(preserved)

    @cached_property
    def downloads(self):
        # TODO: Caching
        return self.versions.aggregate(downloads=Sum("downloads"))["downloads"]

    @property
    def icon(self):
        return self.latest.icon

    @property
    def website_url(self):
        return self.latest.website_url

    @property
    def version_number(self):
        return self.latest.version_number

    @property
    def description(self):
        return self.latest.description

    @property
    def dependencies(self):
        return self.latest.dependencies.all()

    @cached_property
    def sorted_dependencies(self):
        return (
            self.latest.dependencies
            .select_related("package")
            .annotate(total_downloads=Sum("package__versions__downloads"))
            .order_by("-package__is_pinned", "-total_downloads")
        )

    @cached_property
    def is_effectively_active(self):
        return (
            self.is_active and
            self.versions.filter(is_active=True).count() > 0
        )

    @cached_property
    def dependants(self):
        # TODO: Caching
        return Package.objects.exclude(~Q(
            versions__dependencies__package=self,
        )).active()

    @property
    def owner_url(self):
        return reverse("packages.list_by_owner", kwargs={"owner": self.owner.name})

    @property
    def dependants_url(self):
        return reverse(
            "packages.list_by_dependency",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
            }
        )

    @property
    def readme(self):
        return self.latest.readme

    def get_absolute_url(self):
        return reverse(
            "packages.detail",
            kwargs={"owner": self.owner.name, "name": self.name}
        )

    @property
    def full_url(self):
        return "%(protocol)s%(hostname)s%(path)s" % {
            "protocol": settings.PROTOCOL,
            "hostname": settings.SERVER_NAME,
            "path": self.get_absolute_url()
        }

    def recache_latest(self):
        self.latest = self.available_versions.first()
        self.save()

    def handle_created_version(self, version):
        self.date_updated = timezone.now()
        self.is_deprecated = False
        if self.latest:
            new_version = StrictVersion(version.version_number)
            old_version = StrictVersion(self.latest.version_number)
            if new_version > old_version:
                self.latest = version
        else:
            self.latest = version
        self.save()

    def handle_deleted_version(self, version):
        self.recache_latest()

    def __str__(self):
        return self.full_package_name

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)

    @staticmethod
    def post_delete(sender, instance, created, **kwargs):
        invalidate_cache(CacheBustCondition.any_package_updated)


signals.post_save.connect(Package.post_save, sender=Package)
signals.post_delete.connect(Package.post_delete, sender=Package)


def get_version_zip_filepath(instance, filename):
    return f"{instance}.zip"


def get_version_png_filepath(instance, filename):
    return f"{instance}.png"


class PackageVersion(models.Model):
    package = models.ForeignKey(
        Package,
        related_name="versions",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    downloads = models.PositiveIntegerField(
        default=0
    )

    name = models.CharField(
        max_length=Package._meta.get_field("name").max_length,
    )
    version_number = models.CharField(
        max_length=16,
    )
    website_url = models.CharField(
        max_length=1024,
    )
    description = models.CharField(
        max_length=256
    )
    dependencies = models.ManyToManyField(
        "self",
        related_name="dependants",
        symmetrical=False,
        blank=True,
    )
    readme = models.TextField()

    # <packagename>.zip
    file = models.FileField(
        upload_to=get_version_zip_filepath,
        storage=get_storage_class(settings.PACKAGE_FILE_STORAGE)(),
    )
    # <packagename>.png
    icon = models.ImageField(
        upload_to=get_version_png_filepath,
    )
    uuid4 = models.UUIDField(
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        unique_together = ("package", "version_number")

    def get_absolute_url(self):
        return reverse(
            "packages.version.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "version": self.version_number
            }
        )

    @property
    def display_name(self):
        return self.name.replace("_", " ")

    @property
    def owner_url(self):
        return self.package.owner_url

    @property
    def owner(self):
        return self.package.owner

    @property
    def is_deprecated(self):
        return self.package.is_deprecated

    @property
    def full_version_name(self):
        return f"{self.package.full_package_name}-{self.version_number}"

    @property
    def download_url(self):
        return reverse("packages.download", kwargs={
            "owner": self.package.owner.name,
            "name": self.package.name,
            "version": self.version_number,
        })

    @property
    def install_url(self):
        return "ror2mm://v1/install/%(hostname)s/%(owner)s/%(name)s/%(version)s/" % {
            "hostname": settings.SERVER_NAME,
            "owner": self.package.owner.name,
            "name": self.package.name,
            "version": self.version_number,
        }

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        if created:
            instance.package.handle_created_version(instance)
            instance.announce_release()

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        instance.package.handle_deleted_version(instance)

    def announce_release(self):
        webhooks = Webhook.objects.filter(
            webhook_type=WebhookType.mod_release,
            is_active=True,
        )

        thumbnail_url = self.icon.url
        if not (thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://")):
            thumbnail_url = f"{settings.PROTOCOL}{settings.SERVER_NAME}{thumbnail_url}"

        webhook_data = {
            "embeds": [{
                "title": f"{self.name} v{self.version_number}",
                "type": "rich",
                "description": self.description,
                "url": self.package.full_url,
                "timestamp": timezone.now().isoformat(),
                "color": 4474879,
                "thumbnail": {
                    "url": thumbnail_url,
                    "width": 256,
                    "height": 256,
                },
                "provider": {
                    "name": "Thunderstore",
                    "url": f"{settings.PROTOCOL}{settings.SERVER_NAME}/"
                },
                "author": {
                    "name": self.package.owner.name,
                },
                "fields": [{
                    "name": "Total downloads across versions",
                    "value": f"{self.package.downloads}",
                }]
            }]
        }

        for webhook in webhooks:
            webhook.call_with_json(webhook_data)

    def maybe_increase_download_counter(self, request):
        client_ip, is_routable = get_client_ip(request)
        if client_ip is None:
            return

        download_event, created = PackageVersionDownloadEvent.objects.get_or_create(
            version=self,
            source_ip=client_ip,
        )

        if created:
            valid = True
        else:
            valid = download_event.count_downloads_and_return_validity()

        if valid:
            self.downloads += 1
            self.save(update_fields=("downloads",))

    def __str__(self):
        return self.full_version_name


signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)


class PackageVersionDownloadEvent(models.Model):
    version = models.ForeignKey(
        PackageVersion,
        related_name="download_events",
        on_delete=models.CASCADE,
    )
    source_ip = models.GenericIPAddressField()
    last_download = models.DateTimeField(auto_now_add=True)
    total_downloads = models.PositiveIntegerField(
        default=1
    )
    counted_downloads = models.PositiveIntegerField(
        default=1
    )

    def count_downloads_and_return_validity(self):
        self.total_downloads += 1
        is_valid = False

        if self.last_download + timedelta(minutes=10) < timezone.now():
            self.counted_downloads += 1
            self.last_download = timezone.now()
            is_valid = True

        self.save(update_fields=("total_downloads", "counted_downloads", "last_download"))
        return is_valid

    class Meta:
        unique_together = ("version", "source_ip")
