import pytz
from django.db import migrations


def forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*/2",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=pytz.timezone("UTC"),
    )
    PeriodicTask.objects.get_or_create(
        crontab=schedule,
        name="Cleanup expired sessions",
        task="thunderstore.core.tasks.celery_cleanup_sessions",
    )


def backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task="thunderstore.core.tasks.celery_cleanup_sessions",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_adjust_jwt_type_choices"),
        ("django_celery_beat", "0014_remove_clockedschedule_enabled"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
