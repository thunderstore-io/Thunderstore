import pytest

from thunderstore.repository.models import (
    AsyncPackageSubmission,
    PackageSubmissionStatus,
    Team,
    TeamMember,
)
from thunderstore.repository.tasks.submission import (
    _process_submission,
    process_submission_idempotent,
)


@pytest.mark.django_db(transaction=True)
def test_process_submission_idempotency(
    async_package_submission: AsyncPackageSubmission,
):
    assert async_package_submission.status == PackageSubmissionStatus.PENDING
    assert process_submission_idempotent(async_package_submission.pk) is True
    async_package_submission.refresh_from_db()
    assert async_package_submission.status == PackageSubmissionStatus.FINISHED
    assert process_submission_idempotent(async_package_submission.pk) is False


@pytest.mark.django_db(transaction=True)
def test_process_submission_task_error(
    async_package_submission: AsyncPackageSubmission,
    mocker,
    settings,
):
    settings.ALWAYS_RAISE_EXCEPTIONS = False
    mocker.patch(
        "thunderstore.repository.tasks.submission._process_submission",
        side_effect=RuntimeError("Test error"),
    )

    assert async_package_submission.task_error is None
    assert async_package_submission.status == PackageSubmissionStatus.PENDING
    assert process_submission_idempotent(async_package_submission.pk) is True
    async_package_submission.refresh_from_db()
    assert async_package_submission.status == PackageSubmissionStatus.FINISHED
    assert "Test error" in async_package_submission.task_error


@pytest.mark.django_db
def test_process_submission_form_save_errors(
    async_package_submission: AsyncPackageSubmission,
):
    assert async_package_submission.form_errors is None
    _process_submission(async_package_submission)

    # Team is set but filtered out because the user isn't a member of it, so
    # we expect to see errors claiming the team is not set.
    assert "A team must be selected" in str(async_package_submission.form_errors)
