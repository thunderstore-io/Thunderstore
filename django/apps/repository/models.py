from django.conf import settings
from django.db import models
from django.urls import reverse


class Package(models.Model):
    maintainers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="maintaned_packages",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_packages",
    )
    name = models.CharField(
        max_length=128,
    )
    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = ("owner", "name")

    @property
    def full_package_name(self):
        return f"{self.owner.username}-{self.name}"


def get_version_path(instance):
    return f"{instance.package.full_package_name}-{instance.version_number}"


def get_version_zip_filepath(instance, filename):
    return f"{get_version_path(instance)}.zip"


def get_version_png_filepath(instance, filename):
    return f"{get_version_path(instance)}.png"


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

    # manifest.json
    name = models.CharField(
        max_length=Package._meta.get_field("name").max_length,
    )
    version_number = models.CharField(
        max_length=16,
    )
    website_url = models.CharField(
        max_length=1024,
    )

    # <packagename>.zip
    file = models.FileField(
        upload_to=get_version_zip_filepath,
    )
    # <packagename>.png
    icon = models.ImageField(
        upload_to=get_version_png_filepath,
    )

    class Meta:
        unique_together = ("package", "version_number")

    def get_absolute_url(self):
        return reverse("packages.detail", kwargs={"pk": self.package.pk})
