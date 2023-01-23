import django.db.models.deletion
from django.db import migrations, models


def forwards(apps, schema_editor):
    Webhook = apps.get_model("webhooks", "Webhook")
    for x in Webhook.objects.all():
        x.community = x.community_site.community
        x.save()


def backwards(apps, schema_editor):
    Webhook = apps.get_model("webhooks", "Webhook")
    for x in Webhook.objects.all():
        x.community_site = x.community.sites.first()
        x.community = None
        x.save()


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0022_add_block_auto_updates"),
        ("webhooks", "0006_make_community_mandatory"),
    ]

    operations = [
        migrations.AddField(
            model_name="webhook",
            name="community",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="webhooks",
                to="community.community",
            ),
        ),
        migrations.AlterField(
            model_name="webhook",
            name="community_site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="webhooks",
                to="community.CommunitySite",
            ),
        ),
        migrations.RunPython(code=forwards, reverse_code=backwards),
        migrations.AlterField(
            model_name="webhook",
            name="community",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="webhooks",
                to="community.community",
            ),
        ),
    ]
