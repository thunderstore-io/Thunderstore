from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0064_add_namespaces_for_existing_teams"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PackageVersionDownloadEvent",
        ),
    ]
