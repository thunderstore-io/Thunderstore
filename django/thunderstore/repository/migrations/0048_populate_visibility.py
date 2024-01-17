from typing import Iterable, List, TypeVar

from django.db import migrations

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


def forwards(apps, schema_editor):
    PackageVersion = apps.get_model("repository", "PackageVersion")
    VisibilityFlags = apps.get_model("permissions", "VisibilityFlags")

    def get_public_flags():
        return VisibilityFlags(
            public_list=True,
            public_detail=True,
            owner_list=True,
            owner_detail=True,
            moderator_list=True,
            moderator_detail=True,
            admin_list=True,
            admin_detail=True,
        )

    obj_ids = PackageVersion.objects.values_list("id", flat=True).iterator()

    for ids in batch(2000, obj_ids):
        flags = VisibilityFlags.objects.bulk_create(
            (get_public_flags() for _ in range(len(ids)))
        )
        versions = (
            PackageVersion(id=id, visibility=visibility)
            for id, visibility in zip(ids, flags)
        )
        PackageVersion.objects.bulk_update(
            objs=versions,
            fields=["visibility"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0047_add_visibility_flags"),
        ("permissions", "__first__"),
    ]

    operations = [
        migrations.RunPython(code=forwards, reverse_code=migrations.RunPython.noop)
    ]
