# Generated by Django 3.1.7 on 2022-07-13 04:26

import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0034_add_team_donation_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="packageversion",
            name="format_spec",
            field=models.TextField(
                blank=True,
                choices=[
                    ("thunderstore.io:v0.0", "V0 0"),
                    ("thunderstore.io:v0.1", "V0 1"),
                ],
                help_text="Used to track the latest package format spec this package is compatible with",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="packageversion",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("format_spec", None),
                    ("format_spec", "thunderstore.io:v0.0"),
                    ("format_spec", "thunderstore.io:v0.1"),
                    _connector="OR",
                ),
                name="valid_package_format",
            ),
        ),
    ]
