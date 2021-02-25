import pytest

from thunderstore.community.factories import CommunitySiteFactory
from thunderstore.community.models import CommunitySite


@pytest.mark.django_db
def test_community_site_manager_listed():
    c1 = CommunitySiteFactory(is_listed=True)
    c2 = CommunitySiteFactory(is_listed=False)

    listed_communities = CommunitySite.objects.listed()
    assert c1 in listed_communities
    assert c2 not in listed_communities


@pytest.mark.django_db
def test_community_site_full_url(settings):
    site = CommunitySiteFactory(is_listed=True)
    assert site.site.domain in site.full_url
    settings.PROTOCOL = "https://"
    assert site.full_url.startswith("https://")
    settings.PROTOCOL = "http://"
    assert site.full_url.startswith("http://")
