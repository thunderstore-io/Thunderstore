from typing import Any, Dict

from django.conf import settings
from django.db import models, transaction
from django.db.models import Manager, TextChoices
from django.utils import timezone

from thunderstore.core.mixins import TimestampMixin
from thunderstore.repository.utils import has_expired
from thunderstore.usermedia.models import UserMedia


class PackageSubmissionStatus(TextChoices):
    PENDING = "PENDING"
    FINISHED = "FINISHED"


class AsyncPackageSubmission(TimestampMixin):
    objects: "Manager[AsyncPackageSubmission]"
    TASK_TTL = 60 * 5
    CLEANUP_TTL = 60 * 60 * 24

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="async_package_submissions",
        on_delete=models.PROTECT,
    )
    file = models.ForeignKey(
        UserMedia,
        related_name="async_package_submissions",
        on_delete=models.PROTECT,
    )
    status = models.TextField(
        choices=PackageSubmissionStatus.choices,
        default=PackageSubmissionStatus.PENDING,
    )
    datetime_scheduled = models.DateTimeField(blank=True, null=True)
    datetime_finished = models.DateTimeField(blank=True, null=True)
    datetime_polled = models.DateTimeField(auto_now_add=True)

    form_data: Dict[str, Any] = models.JSONField()
    form_errors = models.JSONField(blank=True, null=True)

    task_error = models.TextField(blank=True, null=True)

    created_version = models.OneToOneField(
        "repository.PackageVersion",
        related_name="async_package_submission",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    @transaction.atomic
    def schedule_if_appropriate(self):
        """
        Schedules processing of this submission if it's in a valid state for
        that to happen. Criteria is:
        - No prior task has been scheduled OR enough time has passed
        - The submission is in the PENDING state
        """
        from ..tasks.submission import process_submission_task

        self.datetime_polled = timezone.now()
        if self.status == PackageSubmissionStatus.PENDING and has_expired(
            self.datetime_scheduled, timezone.now(), self.TASK_TTL
        ):
            transaction.on_commit(
                lambda: process_submission_task.delay(submission_id=self.pk)
            )
            self.datetime_scheduled = timezone.now()
        self.save(update_fields=("datetime_scheduled", "datetime_polled"))
