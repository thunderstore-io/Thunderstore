# Generated by Django 3.1.7 on 2024-09-12 02:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("community", "0029_packagelisting_is_auto_imported"),
        ("repository", "0051_bigint_file_size"),
    ]

    operations = [
        migrations.CreateModel(
            name="PackageReport",
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
                ("datetime_created", models.DateTimeField(auto_now_add=True)),
                ("datetime_updated", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.CharField(max_length=255)),
                ("reason", models.CharField(max_length=255)),
                ("is_automated", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="repository.package",
                    ),
                ),
                (
                    "package_listing",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports",
                        to="community.packagelisting",
                    ),
                ),
                (
                    "package_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports",
                        to="repository.packageversion",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="package_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
