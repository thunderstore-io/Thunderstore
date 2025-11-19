from typing import Generator

import celery
import pytest
from django.test import override_settings

from thunderstore.core.tasks import celery_post


def test_celery_setup(celery_app):
    @celery_app.task
    def test_task():
        return "Hello"

    taskrun = test_task.delay()
    result = taskrun.get(timeout=1)
    assert taskrun.successful()
    assert result == "Hello"


KNOWN_CELERY_IDS = (
    "celery.accumulate",
    "celery.chord",
    "celery.chunks",
    "celery.chord_unlock",
    "celery.group",
    "celery.map",
    "celery.chain",
    "celery.starmap",
    "celery.backend_cleanup",
    "thunderstore.community.tasks.update_community_aggregated_fields",
    "thunderstore.core.tasks.celery_post",
    "thunderstore.cache.tasks.invalidate_cache",
    "thunderstore.repository.tasks.update_api_caches",
    "thunderstore.usermedia.tasks.celery_cleanup_expired_uploads",
    "thunderstore.schema_import.tasks.sync_ecosystem_schema",
    "thunderstore.repository.tasks.files.extract_package_version_file_tree",
    "thunderstore.repository.tasks.update_chunked_package_caches",
    "thunderstore.repository.tasks.update_experimental_package_index",
    "thunderstore.repository.tasks.process_package_submission",
    "thunderstore.repository.tasks.cleanup_package_submissions",
    "thunderstore.repository.tasks.log_version_download",
    "thunderstore.webhooks.tasks.process_audit_event",
    "thunderstore.analytics.send_kafka_message",
)


def test_celery_ensure_known_ids_up_to_date(celery_app):
    """
    This test has been written to enforce the addition of new celery tasks to
    the KNOWN_CELERY_IDS. Manual intervention by a developer is required.

    The KNOWN_CELERY_IDS is used in a similar test later on, ensuring that any
    known celery task isn't removed without proper precautions.

    INSTRUCTIONS FOR WHEN THIS TEST FAILS:
        - Add the celery ID that was missing to the KNOWN_CELERY_IDS
    """
    unknown_tasks = []
    for task_id in celery_app.tasks.keys():
        if task_id not in KNOWN_CELERY_IDS:
            unknown_tasks.append(task_id)

    if unknown_tasks:
        pytest.fail(
            "\n\nUnknown celery task IDs:\n"
            + "    "
            + "\n    ".join(unknown_tasks)
            + "\nFollow the instructions written to this test's comments.",
        )


def test_celery_task_removal_handled_correctly(celery_app):
    """
    This test has been written to enforce a checklist when removing or renaming
    celery tasks. If this task fails, it means you've removed or renamed a
    celery task, and need to take appropriate measures.

    THIS TEST EXIST SOLELY TO DELIVER THE FOLLOWING CHECKLIST TO THE DEVELOPER

    INSTRUCTIONS FOR WHEN THIS TEST FAILS:
        1. Make sure the task ID you removed/renamed is not stored anywhere in
          the database
            - We use django-celery-beat for storing task shcedules, which means
              task IDs in the database have to be updated accordingly
        2. If you REMOVED a task, create a database migration that removes or
          disables all task schedules with the removed task's ID
        3. If you RENAMED, REFACTORED, OR MOVED a task, create a database
          migration that modifies all task schedules with the old task ID to
          call the new task(s) appropriately instead
        4. Once you are sure all references to the old task ID have been migrated
          in the database, remove the task ID from KNOWN_CELERY_IDS.
    """
    removed_tasks = []
    known_tasks = set(celery_app.tasks.keys())
    for task in KNOWN_CELERY_IDS:
        if task not in known_tasks:
            removed_tasks.append(task)

    if removed_tasks:
        pytest.fail(
            "\n\nDetected removed celery task IDs:\n"
            + "    "
            + "\n    ".join(removed_tasks)
            + "\nFollow the instructions written to this test's comments.",
        )


@pytest.mark.django_db
@override_settings(CELERY_ALWAYS_EAGER=True)
def test_celery_post(
    celery_app: celery.Celery,
    http_server: Generator[str, None, None],
):
    celery_response = celery_post.delay("http://localhost:8888")
    assert celery_response.state == "SUCCESS"
    assert isinstance(celery_response, celery.result.EagerResult)
