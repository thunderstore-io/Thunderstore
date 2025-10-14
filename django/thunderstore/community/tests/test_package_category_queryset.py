import pytest

from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import PackageCategory


@pytest.mark.django_db
def test_packagecategory_objects_visible_filters_hidden_flag():
    community = CommunityFactory()
    visible = PackageCategory.objects.create(
        community=community, name="Visible", slug="visible", hidden=False
    )
    hidden = PackageCategory.objects.create(
        community=community, name="Hidden", slug="hidden", hidden=True
    )

    result = list(PackageCategory.objects.visible().order_by("slug"))

    assert result == [visible]
    assert hidden not in result


@pytest.mark.django_db
def test_related_manager_visible_on_community_package_categories():
    community = CommunityFactory()
    visible = PackageCategory.objects.create(
        community=community, name="Visible", slug="visible", hidden=False
    )
    PackageCategory.objects.create(
        community=community, name="Hidden", slug="hidden", hidden=True
    )

    result = list(community.package_categories.visible().order_by("slug"))

    assert result == [visible]


@pytest.mark.django_db
def test_related_manager_visible_on_listing_categories():
    listing = PackageListingFactory()
    visible = PackageCategory.objects.create(
        community=listing.community, name="Visible", slug="visible", hidden=False
    )
    hidden = PackageCategory.objects.create(
        community=listing.community, name="Hidden", slug="hidden", hidden=True
    )
    listing.categories.set([visible, hidden])

    result = list(listing.categories.visible().order_by("slug"))

    assert result == [visible]
