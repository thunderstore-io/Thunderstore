from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from thunderstore.community.models import PackageListing
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageVersion
from thunderstore.ts_reports.models._common import ActiveManager

if TYPE_CHECKING:
    from thunderstore.ts_reports.models import PackageReportReason


class PackageReport(TimestampMixin):
    objects = ActiveManager()

    is_active = models.BooleanField(default=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="package_reports",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
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
        on_delete=models.CASCADE,
    )
    reason = models.ForeignKey(
        "ts_reports.PackageReportReason",
        related_name="reports",
        on_delete=models.PROTECT,
    )
    description = models.TextField(blank=True, null=True)

    @classmethod
    def handle_user_report(
        cls,
        submitted_by: UserType,
        package_listing: PackageListing,
        package_version: PackageVersion,
        reason: "PackageReportReason",
        description: Optional[str],
    ) -> "PackageReport":
        return cls.objects.create(
            submitted_by=submitted_by,
            package_listing=package_listing,
            package_version=package_version,
            reason=reason,
            description=description,
        )

    def validate(self):
        if self.package_listing.package != self.package_version.package:
            raise ValidationError("Package mismatch!")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)
