import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("repository", "0066_add_readme_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="packageversion",
            name="readme_override_edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="packageversion",
            name="readme_override_edited_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="readme_overrides",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="packageversion",
            name="changelog_override_edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="packageversion",
            name="changelog_override_edited_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="changelog_overrides",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
