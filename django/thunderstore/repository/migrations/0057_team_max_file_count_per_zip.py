# Generated by Django 3.1.7 on 2025-04-21 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0056_packageversion_uploaded_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="max_file_count_per_zip",
            field=models.IntegerField(
                blank=True,
                help_text="Optional limit on the max number of files in a zip uploaded by this team, replacing the default limit",
                null=True,
            ),
        ),
    ]
