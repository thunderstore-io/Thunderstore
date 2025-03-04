# Generated by Django 3.1.7 on 2024-10-17 19:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("repository", "0055_delete_namespaces_without_team"),
    ]

    operations = [
        migrations.AddField(
            model_name="packageversion",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="uploaded_versions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
