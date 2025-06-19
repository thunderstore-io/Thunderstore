from typing import Iterable, List, TypeVar

from django.db import migrations, models

T = TypeVar("T")


def batch(batch_size: int, iterable: Iterable[T]) -> Iterable[List[T]]:
    collected = []
    for entry in iterable:
        collected.append(entry)
        if len(collected) >= batch_size:
            yield collected
            collected = []
    if len(collected) > 0:
        yield collected


def update_pending_to_unreviewed(apps, schema_editor):
    PackageVersion = apps.get_model("repository", "PackageVersion")

    version_ids = (
        PackageVersion.objects.filter(review_status="skipped")
        .values_list("id", flat=True)
        .iterator()
    )
    for ids in batch(2000, version_ids):
        PackageVersion.objects.filter(id__in=ids).update(review_status="unreviewed")


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0060_create_default_visibility_for_existing_records"),
    ]

    operations = [
        migrations.AlterField(
            model_name="packageversion",
            name="review_status",
            field=models.TextField(
                choices=[
                    ("unreviewed", "unreviewed"),
                    ("approved", "approved"),
                    ("rejected", "rejected"),
                ],
                default="unreviewed",
            ),
        ),
        migrations.RunPython(update_pending_to_unreviewed, migrations.RunPython.noop),
    ]
