import pytz
from django.db import migrations


def forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="20",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=pytz.timezone("UTC"),
    )
    PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name="Cleanup async package submissions",
        task="thunderstore.repository.tasks.cleanup_package_submissions",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0045_add_async_submission"),
        ("django_celery_beat", "0014_remove_clockedschedule_enabled"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
