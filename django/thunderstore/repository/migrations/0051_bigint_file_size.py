# Generated by Django 3.1.7 on 2024-04-07 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0050_add_installer_name_description"),
    ]

    operations = [
        migrations.AlterField(
            model_name="packageversion",
            name="file_size",
            field=models.PositiveBigIntegerField(),
        ),
    ]
