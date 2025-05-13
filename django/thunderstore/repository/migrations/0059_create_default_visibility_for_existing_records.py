from django.db import migrations

from thunderstore.repository.consts import PackageVersionReviewStatus


def create_default_visibility_for_existing_records(apps, schema_editor):
    PackageVersion = apps.get_model("repository", "PackageVersion")
    Package = apps.get_model("repository", "Package")
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
        update_version_visibility(instance)

    for instance in Package.objects.filter(visibility__isnull=True):
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
        update_package_visibility(instance)


def update_version_visibility(version):
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


def update_package_visibility(package):
    package.visibility.public_detail = True
    package.visibility.public_list = True
    package.visibility.owner_detail = True
    package.visibility.owner_list = True
    package.visibility.moderator_detail = True
    package.visibility.moderator_list = True

    if not package.is_active:
        package.visibility.public_detail = False
        package.visibility.public_list = False
        package.visibility.owner_detail = False
        package.visibility.owner_list = False
        package.visibility.moderator_detail = False
        package.visibility.moderator_list = False

    visibility_fields = [
        "public_detail",
        "public_list",
        "owner_detail",
        "owner_list",
        "moderator_detail",
        "moderator_list",
    ]

    versions = list(
        package.versions.filter(is_active=True).values(
            *[f"visibility__{field}" for field in visibility_fields]
        )
    )

    any_version_visible = {field: False for field in visibility_fields}

    for field in visibility_fields:
        for version in versions:
            if version[f"visibility__{field}"]:
                any_version_visible[field] = True
                break

    for field, exists in any_version_visible.items():
        if not exists:
            setattr(package.visibility, field, False)

    package.visibility.save()


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0058_package_visibility"),
    ]

    operations = [
        migrations.RunPython(
            create_default_visibility_for_existing_records, migrations.RunPython.noop
        ),
    ]
