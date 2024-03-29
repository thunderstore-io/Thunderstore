# Generated by Django 3.1.7 on 2023-09-26 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0022_add_block_auto_updates"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="show_decompilation_results",
            field=models.TextField(
                choices=[("NONE", "None"), ("YES", "Yes"), ("NO", "No")], default="NONE"
            ),
        ),
    ]
