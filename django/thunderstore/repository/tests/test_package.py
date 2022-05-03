import pytest

from thunderstore.community.models.package_listing import PackageListing


@pytest.mark.django_db
def test_package_get_owner_url(active_package_listing: PackageListing) -> None:
    owner_url = active_package_listing.package.get_owner_url(
        active_package_listing.community.identifier
    )
    assert owner_url == "/c/test/p/Test_Team/"


@pytest.mark.django_db
def test_package_get_dependants_url(active_package_listing: PackageListing) -> None:
    owner_url = active_package_listing.package.get_dependants_url(
        active_package_listing.community.identifier
    )
    assert (
        owner_url
        == f"/c/test/p/Test_Team/{active_package_listing.package.name}/dependants/"
    )


@pytest.mark.django_db
def test_package_get_page_url(
    active_package_listing: PackageListing,
) -> None:
    owner_url = active_package_listing.package.get_page_url(
        active_package_listing.community.identifier
    )
    assert owner_url == f"/c/test/p/Test_Team/{active_package_listing.package.name}/"
