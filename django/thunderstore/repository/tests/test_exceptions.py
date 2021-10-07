import pytest

from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.exceptions import RedirectListingException


@pytest.mark.django_db
def test_RedirectListingException(active_package_listing: PackageListing):
    exc = RedirectListingException(active_package_listing)
    assert exc.listing == active_package_listing
    assert exc.__str__() == "Listing found in another community"
