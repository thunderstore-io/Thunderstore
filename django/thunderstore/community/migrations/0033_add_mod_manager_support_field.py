# Generated by Django 3.1.7 on 2025-02-24 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0032_add_community_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="has_mod_manager_support",
            field=models.BooleanField(default=True),
        ),
    ]
