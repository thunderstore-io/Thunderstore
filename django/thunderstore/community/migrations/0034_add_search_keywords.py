# Generated by Django 3.1.7 on 2025-03-05 08:35

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0033_add_mod_manager_support_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="search_keywords",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=512),
                blank=True,
                default=list,
                null=True,
                size=None,
            ),
        ),
    ]
