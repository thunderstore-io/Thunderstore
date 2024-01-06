import pytest

from thunderstore.community.factories import CommunitySiteFactory
from thunderstore.community.models import CommunitySite, PackageListing


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
@pytest.mark.parametrize("has_changelog", (False, True))
def test_package_tab_changelog_view(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    has_site: bool,
    has_changelog: bool,
):
    community = active_package_listing.community
    if has_site:
        CommunitySiteFactory(community=community)

    if has_changelog:
        active_package_listing.package.latest.changelog = "# Foo bar"
        active_package_listing.package.latest.save()
        active_package_listing = PackageListing.objects.get(
            pk=active_package_listing.pk
        )

    changelog_url = active_package_listing.get_changelog_url()
    response = client.get(changelog_url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    if has_changelog:
        assert b"Foo bar" in response.content
    else:
        assert b"This package has no changelog" in response.content
