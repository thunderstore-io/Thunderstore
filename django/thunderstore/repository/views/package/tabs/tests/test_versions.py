import pytest

from thunderstore.community.factories import CommunitySiteFactory
from thunderstore.community.models import CommunitySite, PackageListing


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
def test_package_tab_versions_view(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    has_site: bool,
):
    community = active_package_listing.community
    if has_site:
        CommunitySiteFactory(community=community)

    changelog_url = active_package_listing.get_versions_url()
    response = client.get(changelog_url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert (
        active_package_listing.package.latest.version_number.encode()
        in response.content
    )
