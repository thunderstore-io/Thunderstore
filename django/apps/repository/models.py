from distutils.version import StrictVersion

from django.conf import settings
from django.db import models
from django.db.models import Case, When, Sum
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

    @property
    def latest(self):
        # TODO: Caching
        return self.available_versions.first()

    @property
    def available_versions(self):
        # TODO: Caching
        versions = self.versions.filter(is_active=True).values_list("pk", "version_number")
        ordered = sorted(versions, key=lambda version: StrictVersion(version[1]))
        pk_list = [version[0] for version in reversed(ordered)]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_list)])
        return self.versions.filter(pk__in=pk_list).order_by(preserved)

    @property
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
    def readme(self):
        return self.latest.readme

    def get_absolute_url(self):
        return reverse("packages.detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.full_package_name


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
    readme = models.TextField()

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
        return self.package.get_absolute_url()

    @property
    def full_version_name(self):
        return f"{self.package.full_package_name}-{self.version_number}"

    @property
    def download_url(self):
        return reverse("packages.download", kwargs={
            "owner": self.package.owner.username,
            "name": self.package.name,
            "version": self.version_number,
        })

    @property
    def install_url(self):
        return "lspm://%(hostname)s/%(owner)s/%(name)s/%(version)s/" % {
            "hostname": settings.SERVER_NAME,
            "owner": self.package.owner.username,
            "name": self.package.name,
            "version": self.version_number,
        }

    def __str__(self):
        return self.full_version_name
