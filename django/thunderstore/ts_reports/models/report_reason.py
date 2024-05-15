from django.db import models

from thunderstore.core.mixins import TimestampMixin
from thunderstore.ts_reports.models._common import ActiveManager


class PackageReportReason(TimestampMixin):
    objects = ActiveManager()

    label = models.TextField()
    is_active = models.BooleanField(default=True)
