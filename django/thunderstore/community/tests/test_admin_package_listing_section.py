import pytest

from thunderstore.community.admin.package_listing_section import (
    PackageListingSectionAdmin,
    set_listed,
    set_unlisted,
)
from thunderstore.community.models import Community, PackageListingSection


@pytest.mark.django_db
def test_admin_package_listing_section_set_unlisted(community: Community) -> None:
    listings = [
        PackageListingSection.objects.create(
            community=community,
            name=f"Test Listing {i}",
            slug=f"test-listing-{i}",
            is_listed=True,
        )
        for i in range(5)
    ]

    modeladmin = PackageListingSectionAdmin(PackageListingSection, None)
    set_unlisted(modeladmin, None, PackageListingSection.objects.all())

    for entry in listings:
        entry.refresh_from_db()
        assert entry.is_listed is False


@pytest.mark.django_db
def test_admin_package_listing_section_set_listed(community: Community) -> None:
    listings = [
        PackageListingSection.objects.create(
            community=community,
            name=f"Test Listing {i}",
            slug=f"test-listing-{i}",
            is_listed=False,
        )
        for i in range(5)
    ]

    modeladmin = PackageListingSectionAdmin(PackageListingSection, None)
    set_listed(modeladmin, None, PackageListingSection.objects.all())

    for entry in listings:
        entry.refresh_from_db()
        assert entry.is_listed is True


@pytest.mark.django_db
def test_admin_package_listing_section_readonly_fields(
    package_listing_section: PackageListingSection,
) -> None:
    modeladmin = PackageListingSectionAdmin(PackageListingSection, None)
    assert modeladmin.get_readonly_fields(None, None) == []
    assert (
        modeladmin.get_readonly_fields(None, package_listing_section)
        == PackageListingSectionAdmin.readonly_fields
    )
