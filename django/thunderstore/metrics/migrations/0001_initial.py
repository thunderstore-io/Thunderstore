# Generated by Django 3.1.7 on 2023-12-14 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PackageVersionDownloadEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("version_id", models.BigIntegerField(db_index=True)),
                ("timestamp", models.DateTimeField()),
            ],
        ),
    ]