from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from django.db import connection, connections, transaction
from django.utils import timezone
from freezegun.api import FrozenDateTimeFactory

from thunderstore.community.factories import CommunityFactory, PackageCategoryFactory
from thunderstore.community.models import Community
from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    AsyncPackageSubmission,
    PackageSubmissionStatus,
    Team,
    TeamMember,
    TeamMemberRole,
)


@pytest.mark.django_db(transaction=True)
def test_async_package_submission_flow(
    user: UserType,
    manifest_v1_data: Dict[str, Any],
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    com2 = CommunityFactory()
    com3 = CommunityFactory()
    com2_cat1 = PackageCategoryFactory(community=com2)
    com3_cat1 = PackageCategoryFactory(community=com3)
    com3_cat2 = PackageCategoryFactory(community=com3)

    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    submission: AsyncPackageSubmission = AsyncPackageSubmission.objects.create(
        owner=user,
        file_id=manifest_v1_package_upload_id,
        form_data={
            "author_name": team.name,
            "community_categories": {
                com2.identifier: [com2_cat1.slug],
                com3.identifier: [com3_cat1.slug, com3_cat2.slug],
            },
            "communities": [
                community.identifier,
                com2.identifier,
                com3.identifier,
            ],
            "has_nsfw_content": True,
        },
    )
    assert submission.status == PackageSubmissionStatus.PENDING
    assert submission.datetime_scheduled is None
    submission.schedule_if_appropriate()
    submission.refresh_from_db()
    assert submission.datetime_scheduled is not None
    assert submission.status == PackageSubmissionStatus.FINISHED

    assert submission.form_errors is None
    assert submission.task_error is None
    assert submission.created_version is not None
    assert submission.created_version.package.namespace.name == team.name
    assert submission.created_version.name == manifest_v1_data["name"]
    assert (
        submission.created_version.version_number == manifest_v1_data["version_number"]
    )


@contextmanager
def lock_row(instance):
    """
    Hold a FOR UPDATE lock on the instance's row from a second database
    connection, the way the processing task does while it runs.
    """
    other = connections.create_connection("default")
    try:
        other.set_autocommit(False)
        with other.cursor() as cursor:
            cursor.execute(
                f"SELECT 1 FROM {instance._meta.db_table} WHERE id = %s FOR UPDATE",
                [instance.pk],
            )
        yield
    finally:
        other.close()


@pytest.fixture()
def process_submission_delay(mocker) -> MagicMock:
    return mocker.patch(
        "thunderstore.repository.tasks.submission.process_submission_task.delay",
    )


@pytest.mark.django_db(transaction=True)
def test_schedule_if_appropriate_skips_locked_row(
    async_package_submission: AsyncPackageSubmission,
    process_submission_delay: MagicMock,
):
    submission = async_package_submission
    polled_before = submission.datetime_polled

    with lock_row(submission), transaction.atomic():
        # A regression would wait on the lock; fail fast instead of hanging.
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '2s'")
        assert submission.schedule_if_appropriate() is False

    process_submission_delay.assert_not_called()
    submission.refresh_from_db()
    assert submission.datetime_polled == polled_before
    assert submission.datetime_scheduled is None


@pytest.mark.django_db(transaction=True)
def test_schedule_if_appropriate_schedules_pending_submission(
    async_package_submission: AsyncPackageSubmission,
    process_submission_delay: MagicMock,
    freezer: FrozenDateTimeFactory,
):
    submission = async_package_submission
    freezer.tick(timedelta(seconds=1))

    assert submission.schedule_if_appropriate() is True

    process_submission_delay.assert_called_once_with(submission_id=submission.pk)
    submission.refresh_from_db()
    assert submission.datetime_scheduled == timezone.now()
    assert submission.datetime_polled == timezone.now()


@pytest.mark.django_db(transaction=True)
def test_schedule_if_appropriate_reschedules_after_ttl(
    async_package_submission: AsyncPackageSubmission,
    process_submission_delay: MagicMock,
    freezer: FrozenDateTimeFactory,
):
    submission = async_package_submission
    submission.schedule_if_appropriate()
    scheduled_at = timezone.now()
    process_submission_delay.reset_mock()

    freezer.tick(timedelta(seconds=AsyncPackageSubmission.TASK_TTL))
    submission.schedule_if_appropriate()
    process_submission_delay.assert_not_called()
    submission.refresh_from_db()
    assert submission.datetime_scheduled == scheduled_at
    assert submission.datetime_polled == timezone.now()

    freezer.tick(timedelta(seconds=1))
    submission.schedule_if_appropriate()
    process_submission_delay.assert_called_once_with(submission_id=submission.pk)
    submission.refresh_from_db()
    assert submission.datetime_scheduled == timezone.now()


@pytest.mark.django_db(transaction=True)
def test_schedule_if_appropriate_ignores_finished_submission(
    async_package_submission: AsyncPackageSubmission,
    process_submission_delay: MagicMock,
    freezer: FrozenDateTimeFactory,
):
    submission = async_package_submission
    submission.status = PackageSubmissionStatus.FINISHED
    submission.save()
    freezer.tick(timedelta(seconds=1))

    assert submission.schedule_if_appropriate() is True

    process_submission_delay.assert_not_called()
    submission.refresh_from_db()
    assert submission.datetime_scheduled is None
    assert submission.datetime_polled == timezone.now()
