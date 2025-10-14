from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0037_create_default_visibility_for_existing_listings"),
    ]

    operations = [
        migrations.AddField(
            model_name="packagecategory",
            name="hidden",
            field=models.BooleanField(default=False),
        ),
    ]
