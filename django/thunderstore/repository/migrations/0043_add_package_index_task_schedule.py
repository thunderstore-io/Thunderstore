import pytz
from django.db import migrations


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
        name="Update experimental API package index cache",
        task="thunderstore.repository.tasks.update_experimental_package_index",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0042_add_package_index_cache"),
        ("django_celery_beat", "0014_remove_clockedschedule_enabled"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
