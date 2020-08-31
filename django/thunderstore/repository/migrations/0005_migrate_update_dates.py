from distutils.version import StrictVersion

from django.db import migrations
from django.db.models import Case, When


def get_latest_version(package):
    versions = package.versions.values_list("pk", "version_number")
    ordered = sorted(versions, key=lambda version: StrictVersion(version[1]))
    pk_list = [version[0] for version in reversed(ordered)]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_list)])
    return package.versions.filter(pk__in=pk_list).order_by(preserved).first()


def migrate_update_dates(apps, schema_editor):
    Package = apps.get_model("repository", "Package")
    for package in Package.objects.all():
        latest = get_latest_version(package)
        package.date_updated = latest.date_created
        package.save()


class Migration(migrations.Migration):

    dependencies = [
        ('repository', '0004_add_update_date'),
    ]

    operations = [
        migrations.RunPython(migrate_update_dates),
    ]
