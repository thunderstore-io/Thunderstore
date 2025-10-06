import traceback
from datetime import timedelta

from thunderstore.core.kafka import KafkaTopics, SubmissionEvents
from ts_kafka.producer import publish_event

from celery import shared_task
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from thunderstore.core.exception_handler import serialize_validation_error
from thunderstore.core.settings import CeleryQueues
from thunderstore.core.utils import capture_exception
from thunderstore.repository.models import (
    AsyncPackageSubmission,
    PackageSubmissionStatus,
)
from thunderstore.repository.package_upload import PackageUploadForm
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import download_file


@shared_task(
    queue=CeleryQueues.BackgroundTask,
    name="thunderstore.repository.tasks.process_package_submission",
)
def process_submission_task(submission_id: str):
    process_submission_idempotent(submission_id)


@shared_task(
    queue=CeleryQueues.BackgroundLongRunning,
    name="thunderstore.repository.tasks.cleanup_package_submissions",
)
def cleanup_submissions_task():
    cleanup_submissions()


def cleanup_submissions():
    ttl_threshold = timezone.now() - timedelta(
        seconds=AsyncPackageSubmission.CLEANUP_TTL,
    )
    AsyncPackageSubmission.objects.filter(
        Q(~Q(datetime_finished=None) & Q(datetime_finished__lt=ttl_threshold))
        | Q(datetime_polled__lt=ttl_threshold)
    ).delete()


@transaction.atomic
def process_submission_idempotent(submission_id: str) -> bool:
    """
    Process a submission by ID with idempotency guarantees.

    :param submission_id: The submission to process
    :return: 'True' if processing was needed, 'False' if it could be skipped.
    """
    submission = (
        AsyncPackageSubmission.objects.select_for_update(skip_locked=True)
        .filter(pk=submission_id, status=PackageSubmissionStatus.PENDING)
        .first()
    )
    if not submission:
        return False

    try:
        _process_submission(submission)
    except Exception as e:
        capture_exception(e)
        submission.task_error = traceback.format_exc()
    finally:
        submission.status = PackageSubmissionStatus.FINISHED
        submission.datetime_finished = timezone.now()
        submission.save()

    return True


def _process_submission(submission: AsyncPackageSubmission):
    client = get_s3_client()
    file = download_file(submission.owner, client, submission.file)
    data = submission.form_data

    form = PackageUploadForm(
        user=submission.owner,
        community=None,
        data={
            "community_categories": data.get("community_categories", {}),
            "has_nsfw_content": data.get("has_nsfw_content"),
            "team": data.get("author_name"),
            "communities": data.get("communities"),
        },
        files={"file": file},
    )

    if form.is_valid():
        try:
            submission.created_version = form.save()

            transaction.on_commit(
                lambda: publish_event(
                    KafkaTopics.METRICS_SUBMISSIONS,
                    key=SubmissionEvents.SUBMISSION_SUCCESS,
                    value={
                        "submission_id": submission.id,
                        "user_id": submission.owner.id,
                        "package_id": submission.created_version.package.uuid,
                        "version_number": submission.created_version.version_number,
                    }
                )
            )
        except ValidationError as e:
            submission.form_errors = serialize_validation_error(e)
    else:
        error = ValidationError(form.errors)
        submission.form_errors = serialize_validation_error(error)
