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
    Namespace = apps.get_model("repository", "Namespace")
    Team = apps.get_model("repository", "Team")

    existing_team_ids = set(Namespace.objects.values_list("team_id", flat=True))

    for entry in batch(
        2000,
        map(
            lambda x: Namespace(team_id=x["id"], name=x["name"]),
            filter(
                lambda t: t["id"] not in existing_team_ids,
                Team.objects.values("id", "name"),
            ),
        ),
    ):
        Namespace.objects.bulk_create(entry)


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0063_make_namespaces_cascade_with_teams"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
