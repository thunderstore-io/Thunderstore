# Generated by Django 3.0.4 on 2020-09-04 06:07

import re

import django.core.files.storage
import django.core.validators
from django.db import migrations, models

import thunderstore.repository.models.package_version
import thunderstore.utils.makemigrations


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0021_set_file_size_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="packageversion",
            name="file",
            field=models.FileField(
                storage=thunderstore.utils.makemigrations.StubStorage(),
                upload_to=thunderstore.repository.models.package_version.get_version_zip_filepath,
            ),
        ),
        migrations.AlterField(
            model_name="uploaderidentity",
            name="name",
            field=models.CharField(
                max_length=64,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Author names can only contain a-Z A-Z 0-9 . _ - characers",
                        regex=re.compile("^[a-zA-Z0-9\\_\\.\\-]+$"),
                    )
                ],
            ),
        ),
    ]
