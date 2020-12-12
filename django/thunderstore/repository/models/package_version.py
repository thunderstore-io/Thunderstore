import re
import uuid

from django.core.exceptions import ValidationError
from ipware import get_client_ip

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.db import models
from django.db.models import Sum, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from thunderstore.repository.consts import PACKAGE_NAME_REGEX
from thunderstore.repository.models import Package, PackageVersionDownloadEvent

from thunderstore.webhooks.models import Webhook


def get_version_zip_filepath(instance, filename):
    return f"repository/packages/{instance}.zip"


def get_version_png_filepath(instance, filename):
    return f"repository/icons/{instance}.png"


class PackageVersion(models.Model):
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
    downloads = models.PositiveIntegerField(
        default=0
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
    file_size = models.PositiveIntegerField()

    # <packagename>.png
    icon = models.ImageField(
        upload_to=get_version_png_filepath,
    )
    uuid4 = models.UUIDField(
        default=uuid.uuid4,
        editable=False
    )

    def validate(self):
        if not re.match(PACKAGE_NAME_REGEX, self.name):
            raise ValidationError("Package names can only contain a-Z A-Z 0-9 _ characers")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

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

    @cached_property
    def display_name(self):
        return self.name.replace("_", " ")

    @cached_property
    def owner_url(self):
        return self.package.owner_url

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
    def download_url(self):
        return reverse("packages.download", kwargs={
            "owner": self.package.owner.name,
            "name": self.package.name,
            "version": self.version_number,
        })

    def get_install_url(self, request):
        return "ror2mm://v1/install/%(hostname)s/%(owner)s/%(name)s/%(version)s/" % {
            "hostname": request.site.domain,
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

    def announce_release(self):
        webhooks = Webhook.get_for_package_release(self.package)
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
            self._increase_download_counter()

    def _increase_download_counter(self):
        self.downloads += 1
        self.save(update_fields=("downloads",))

    def __str__(self):
        return self.full_version_name


signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
