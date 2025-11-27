from django.db import migrations


def forwards(apps, schema_editor):
    Namespace = apps.get_model("repository", "Namespace")

    Namespace.objects.filter(team__isnull=True, packages=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0061_alter_packageversion_review"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
