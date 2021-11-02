import django.db.models.deletion
from django.db import migrations, models


def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Namespace = apps.get_model("repository", "Namespace")
    Team = apps.get_model("repository", "Team")
    db_alias = schema_editor.connection.alias
    teams = Team.objects.using(db_alias).all().order_by("id")
    for team in teams:
        new_namespace = Namespace.objects.using(db_alias).create(name=team.name)
        team.namespaces.add(new_namespace)
        team.save()


class Migration(migrations.Migration):

    dependencies = [("repository", "0028_move_package_ownership_to_namespace")]

    operations = [
        migrations.RunPython(forwards_func),
        migrations.AlterField(
            model_name="package",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_packages",
                to="repository.namespace",
            ),
        ),
    ]
