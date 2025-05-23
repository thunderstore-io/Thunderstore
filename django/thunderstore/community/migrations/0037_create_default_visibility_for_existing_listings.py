from django.db import migrations

from thunderstore.community.consts import PackageListingReviewStatus


def create_default_visibility_for_existing_records(apps, schema_editor):
    PackageListing = apps.get_model("community", "PackageListing")
    VisibilityFlags = apps.get_model("permissions", "VisibilityFlags")

    for instance in PackageListing.objects.filter(visibility__isnull=True):
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


def update_visibility(listing):
    package = listing.package
    listing.visibility.public_detail = package.visibility.public_detail
    listing.visibility.public_list = package.visibility.public_list
    listing.visibility.owner_detail = package.visibility.owner_detail
    listing.visibility.owner_list = package.visibility.owner_list
    listing.visibility.moderator_detail = package.visibility.moderator_detail
    listing.visibility.moderator_list = package.visibility.moderator_list
    listing.visibility.admin_detail = package.visibility.admin_detail
    listing.visibility.admin_list = package.visibility.admin_list

    if listing.review_status == PackageListingReviewStatus.rejected:
        listing.visibility.public_detail = False
        listing.visibility.public_list = False

    if (
        listing.community.require_package_listing_approval
        and listing.review_status == PackageListingReviewStatus.unreviewed
    ):
        listing.visibility.public_detail = False
        listing.visibility.public_list = False

    listing.visibility.save()


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0036_packagelisting_visibility"),
        ("repository", "0059_package_visibility"),
        ("repository", "0060_create_default_visibility_for_existing_records"),
    ]

    operations = [
        migrations.RunPython(
            create_default_visibility_for_existing_records, migrations.RunPython.noop
        ),
    ]
