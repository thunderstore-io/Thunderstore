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
    listing.visibility.public_detail = True
    listing.visibility.public_list = True
    listing.visibility.owner_detail = True
    listing.visibility.owner_list = True
    listing.visibility.moderator_detail = True
    listing.visibility.moderator_list = True

    if not listing.package.is_active:
        listing.visibility.public_detail = False
        listing.visibility.public_list = False
        listing.visibility.owner_detail = False
        listing.visibility.owner_list = False
        listing.visibility.moderator_detail = False
        listing.visibility.moderator_list = False

    if listing.review_status == PackageListingReviewStatus.rejected:
        listing.visibility.public_detail = False
        listing.visibility.public_list = False

    if (
        listing.community.require_package_listing_approval
        and listing.review_status == PackageListingReviewStatus.unreviewed
    ):
        listing.visibility.public_detail = False
        listing.visibility.public_list = False

    versions = listing.package.versions.filter(is_active=True).all()
    if versions.exclude(visibility__public_detail=False).count() == 0:
        listing.visibility.public_detail = False
    if versions.exclude(visibility__public_list=False).count() == 0:
        listing.visibility.public_list = False
    if versions.exclude(visibility__owner_detail=False).count() == 0:
        listing.visibility.owner_detail = False
    if versions.exclude(visibility__owner_list=False).count() == 0:
        listing.visibility.owner_list = False
    if versions.exclude(visibility__moderator_detail=False).count() == 0:
        listing.visibility.moderator_detail = False
    if versions.exclude(visibility__moderator_list=False).count() == 0:
        listing.visibility.moderator_list = False

    listing.visibility.save()


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0035_packagelisting_visibility"),
        ("repository", "0058_create_default_visibility_for_existing_versions"),
    ]

    operations = [
        migrations.RunPython(
            create_default_visibility_for_existing_records, migrations.RunPython.noop
        ),
    ]
