from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from thunderstore.community.models import PackageListing
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageVersion
from thunderstore.ts_reports.models._common import ActiveManager


class PackageReport(TimestampMixin):
    objects = ActiveManager()

    is_active = models.BooleanField(default=True)

    category = models.CharField(max_length=255)
    reason = models.CharField(max_length=255)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="package_reports",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    is_automated = models.BooleanField(default=True)

    package = models.ForeignKey(
        "repository.Package",
        related_name="reports",
        on_delete=models.CASCADE,
    )
    package_listing = models.ForeignKey(
        "community.PackageListing",
        related_name="reports",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    package_version = models.ForeignKey(
        "repository.PackageVersion",
        related_name="reports",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.category} : {self.reason}"

    @classmethod
    def handle_user_report(
        cls,
        category: str,
        reason: str,
        submitted_by: UserType,
        package: Package,
        package_listing: PackageListing,
        package_version: PackageVersion,
        description: Optional[str],
    ) -> "PackageReport":
        return cls.objects.create(
            category=category,
            reason=reason,
            submitted_by=submitted_by,
            package=package,
            package_listing=package_listing,
            package_version=package_version,
            description=description,
            is_automated=False,
        )

    def validate(self):
        if self.package_listing:
            if self.package_listing.package != self.package:
                raise ValidationError("Package mismatch!")
        if self.package_version:
            if self.package_version.package != self.package:
                raise ValidationError("Package mismatch!")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)
