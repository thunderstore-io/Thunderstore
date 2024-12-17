from django.db import migrations

from thunderstore.repository.consts import PackageVersionReviewStatus


def create_default_visibility_for_existing_records(apps, schema_editor):
    PackageVersion = apps.get_model("repository", "PackageVersion")
    VisibilityFlags = apps.get_model("permissions", "VisibilityFlags")

    for instance in PackageVersion.objects.filter(visibility__isnull=True):
        visibility_flags = VisibilityFlags.objects.create(
            public_list=False,
            public_detail=False,
            owner_list=True,
            owner_detail=True,
            moderator_list=True,
            moderator_detail=True,
            admin_list=True,
            admin_detail=True,
        )
        instance.visibility = visibility_flags
        instance.save()
        update_visibility(instance)


def update_visibility(version):
    version.visibility.public_detail = True
    version.visibility.public_list = True
    version.visibility.owner_detail = True
    version.visibility.owner_list = True
    version.visibility.moderator_detail = True
    version.visibility.moderator_list = True

    if not version.is_active or not version.package.is_active:
        version.visibility.public_detail = False
        version.visibility.public_list = False
        version.visibility.owner_detail = False
        version.visibility.owner_list = False
        version.visibility.moderator_detail = False
        version.visibility.moderator_list = False

    if (
        version.review_status == PackageVersionReviewStatus.rejected
        or version.review_status == PackageVersionReviewStatus.pending
    ):
        version.visibility.public_detail = False
        version.visibility.public_list = False

    version.visibility.save()


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0055_packageversion_review_status"),
    ]

    operations = [
        migrations.RunPython(
            create_default_visibility_for_existing_records, migrations.RunPython.noop
        ),
    ]
