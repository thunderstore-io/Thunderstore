# Generated by Django 3.1.7 on 2023-07-19 07:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import django_extrafields.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("account", "0003_add_user_flag"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    django_extrafields.models.SafeOneToOneOrField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "user settings",
                "verbose_name_plural": "user settings",
            },
        ),
    ]
