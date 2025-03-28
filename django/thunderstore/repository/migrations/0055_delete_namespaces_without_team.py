# Generated by Django 3.1.7 on 2025-01-07 15:07

from django.db import migrations


def forwards(apps, schema_editor):
    Namespace = apps.get_model("repository", "Namespace")

    Namespace.objects.filter(team__isnull=True, packages=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0054_alter_chunked_package_cache_index"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
