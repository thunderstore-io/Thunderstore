from importlib import import_module

import pytest
from django.apps import apps
from django_celery_beat.models import PeriodicTask


@pytest.mark.django_db
def test_session_cleanup_schedule_migration_forwards_and_backwards():
    migration = import_module(
        "thunderstore.core.migrations.0004_add_session_cleanup_schedule"
    )
    tasks = PeriodicTask.objects.filter(
        task="thunderstore.core.tasks.celery_cleanup_sessions",
    )

    migration.forwards(apps, None)
    migration.forwards(apps, None)

    task = tasks.get()
    assert task.name == "Cleanup expired sessions"
    assert task.enabled
    assert (task.crontab.minute, task.crontab.hour) == ("30", "8")

    migration.backwards(apps, None)

    assert not tasks.exists()
