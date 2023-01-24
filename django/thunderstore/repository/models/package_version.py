import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.db import models
from django.db.models import Manager, QuerySet, Sum, signals
from django.urls import reverse
from django.utils.functional import cached_property
from ipware import get_client_ip

from thunderstore.repository.consts import PACKAGE_NAME_REGEX
from thunderstore.repository.models import Package, PackageVersionDownloadEvent
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.utils.decorators import run_after_commit
from thunderstore.webhooks.models import Webhook


def get_version_zip_filepath(instance, filename):
    return f"repository/packages/{instance}.zip"


def get_version_png_filepath(instance, filename):
    return f"repository/icons/{instance}.png"


class PackageVersionManager(models.Manager):
    def active(self) -> "QuerySet[PackageVersion]":  # TODO: Generic type
        return self.exclude(is_active=False)


class PackageVersion(models.Model):
    objects: "Manager[PackageVersion]" = PackageVersionManager()

    package = models.ForeignKey(
        "repository.Package",
        related_name="versions",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    downloads = models.PositiveIntegerField(default=0)

    format_spec = models.TextField(
        choices=PackageFormats.choices,
        blank=True,
        null=True,
        help_text="Used to track the latest package format spec this package is compatible with",
    )
    name = models.CharField(
        max_length=Package._meta.get_field("name").max_length,
    )

    # TODO: Split to three fields for each number in the version for better querying performance
    version_number = models.CharField(
        max_length=16,
    )
    website_url = models.CharField(
        max_length=1024,
    )
    description = models.CharField(max_length=256)
    dependencies = models.ManyToManyField(
        "self",
        related_name="dependants",
        symmetrical=False,
        blank=True,
    )
    readme = models.TextField()
    changelog = models.TextField(blank=True, null=True)

    # <packagename>.zip
    file = models.FileField(
        upload_to=get_version_zip_filepath,
        storage=get_storage_class(settings.PACKAGE_FILE_STORAGE)(),
    )
    file_size = models.PositiveIntegerField()

    # <packagename>.png
    icon = models.ImageField(
        upload_to=get_version_png_filepath,
    )
    uuid4 = models.UUIDField(default=uuid.uuid4, editable=False)

    def validate(self):
        if not re.match(PACKAGE_NAME_REGEX, self.name):
            raise ValidationError(
                "Package names can only contain a-Z A-Z 0-9 _ characers"
            )

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("package", "version_number"), name="unique_version_per_package"
            ),
            models.CheckConstraint(
                check=PackageFormats.as_query_filter(
                    field_name="format_spec",
                    allow_none=True,
                ),
                name="valid_package_format",
            ),
        ]

    # TODO: Remove in the end of TS-272
    def get_absolute_url(self):
        return reverse(
            "old_urls:packages.version.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "version": self.version_number,
            },
        )

    def get_page_url(self, community_identifier: str) -> str:
        return reverse(
            "communities:community:packages.version.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "version": self.version_number,
                "community_identifier": community_identifier,
            },
        )

    @cached_property
    def display_name(self):
        return self.name.replace("_", " ")

    @cached_property
    def owner(self):
        return self.package.owner

    @cached_property
    def is_deprecated(self):
        return self.package.is_deprecated

    @cached_property
    def full_version_name(self):
        return f"{self.package.full_package_name}-{self.version_number}"

    @cached_property
    def reference(self):
        from thunderstore.repository.package_reference import PackageReference

        return PackageReference(
            namespace=self.owner.name,
            name=self.name,
            version=self.version_number,
        )

    @cached_property
    def _download_url(self):
        return reverse(
            "old_urls:packages.download",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
                "version": self.version_number,
            },
        )

    @cached_property
    def full_download_url(self) -> str:
        return "%(protocol)s%(hostname)s%(path)s" % {
            "protocol": settings.PROTOCOL,
            "hostname": settings.PRIMARY_HOST,
            "path": self._download_url,
        }

    @property
    def install_url(self):
        return "ror2mm://v1/install/%(hostname)s/%(owner)s/%(name)s/%(version)s/" % {
            "hostname": settings.PRIMARY_HOST,
            "owner": self.package.owner.name,
            "name": self.package.name,
            "version": self.version_number,
        }

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        if created:
            instance.package.handle_created_version(instance)
            instance.announce_release()
        instance.package.handle_updated_version(instance)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        instance.package.handle_deleted_version(instance)

    @classmethod
    def get_total_used_disk_space(cls):
        return cls.objects.aggregate(total=Sum("file_size"))["total"] or 0

    @run_after_commit
    def announce_release(self):
        webhooks = Webhook.get_for_package_release(self.package)

        for webhook in webhooks:
            webhook.post_package_version_release(self)

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
            self._increase_download_counter()

    def _increase_download_counter(self):
        self.downloads += 1
        self.save(update_fields=("downloads",))

    def __str__(self):
        return self.full_version_name


signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
