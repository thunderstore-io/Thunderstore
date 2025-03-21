import pytz
from django.db import migrations

TASK = "thunderstore.repository.tasks.update_chunked_package_caches_lc"


def forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=pytz.timezone("UTC"),
    )

    PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name="Update APIV1ChunkedPackageCache (Lethal Company)",
        task=TASK,
        expire_seconds=300,
    )


def backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=TASK).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("repository", "0056_packageversion_uploaded_by"),
        ("django_celery_beat", "0014_remove_clockedschedule_enabled"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
