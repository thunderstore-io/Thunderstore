import pytz
from django.db import migrations


def forwards(apps, _):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="0",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=pytz.timezone("UTC"),
    )
    PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name="Clean up orphan comments",
        task="thunderstore.repository.tasks.clean_up_comments",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0024_comment"),
        ("django_celery_beat", "0014_remove_clockedschedule_enabled"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
