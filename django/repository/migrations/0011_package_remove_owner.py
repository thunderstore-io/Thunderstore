# Generated by Django 2.1.2 on 2019-05-07 19:33

from django.db import migrations


def forwards(apps, schema_editor):
    Package = apps.get_model("repository", "Package")

    for package in Package.objects.all():
        package.owner = None
        package.save()


def backwards(apps, schema_editor):
    Package = apps.get_model("repository", "Package")
    User = apps.get_model("auth", "User")

    for package in Package.objects.all():
        owner = User.objects.get(username=package.uploader.name)
        package.owner = owner
        package.save()


class Migration(migrations.Migration):

    dependencies = [("repository", "0010_package_uploader_field")]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterUniqueTogether(
            name="package", unique_together={("uploader", "name")}
        ),
        migrations.RemoveField(model_name="package", name="owner"),
        migrations.RenameField(
            model_name="package", old_name="uploader", new_name="owner"
        ),
        migrations.AlterUniqueTogether(
            name="package", unique_together={("owner", "name")}
        ),
    ]
