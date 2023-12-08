from datetime import timedelta

import pytest
from django.utils import timezone

from thunderstore.repository.factories import AsyncPackageSubmissionFactory
from thunderstore.repository.models import AsyncPackageSubmission
from thunderstore.repository.tasks import cleanup_submissions_task


@pytest.mark.django_db
def test_cleanup_submissions_task():
    now = timezone.now()
    expiry_threshold = now - timedelta(seconds=AsyncPackageSubmission.CLEANUP_TTL + 1)

    expired_submissions = [
        AsyncPackageSubmissionFactory(
            # Django overrides this due to auto_now_add
            # datetime_polled=expiry_threshold,
            datetime_finished=None,
        ),
        AsyncPackageSubmissionFactory(
            # Django overrides this due to auto_now_add
            # datetime_polled=expiry_threshold,
            datetime_finished=now,
        ),
        AsyncPackageSubmissionFactory(
            datetime_polled=now,
            datetime_finished=expiry_threshold,
        ),
    ]

    # Need to update the timestamp post-creation due to
    # auto_now_add behavior
    for entry in expired_submissions[:2]:
        entry.datetime_polled = expiry_threshold
        entry.save()

    active_submissions = [
        AsyncPackageSubmissionFactory(
            datetime_finished=None,
        ),
        AsyncPackageSubmissionFactory(
            datetime_finished=now,
        ),
    ]

    cleanup_submissions_task()

    assert (
        AsyncPackageSubmission.objects.filter(
            pk__in=(x.pk for x in expired_submissions)
        ).count()
    ) == 0
    assert (
        AsyncPackageSubmission.objects.filter(
            pk__in=(x.pk for x in active_submissions)
        ).count()
    ) == 2
