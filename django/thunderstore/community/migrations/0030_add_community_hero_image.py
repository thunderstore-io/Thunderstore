# Generated by Django 3.1.7 on 2024-11-12 15:39

from django.db import migrations, models

import thunderstore.community.models.community


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0029_packagelisting_is_auto_imported"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="hero_image",
            field=models.ImageField(
                blank=True,
                height_field="hero_image_height",
                null=True,
                upload_to=thunderstore.community.models.community.get_community_filepath,
                width_field="hero_image_width",
            ),
        ),
        migrations.AddField(
            model_name="community",
            name="hero_image_height",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="community",
            name="hero_image_width",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
