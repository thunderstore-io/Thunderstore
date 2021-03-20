import pytest

from thunderstore.community.factories import CommunityFactory
from thunderstore.community.models import Community


@pytest.mark.django_db
def test_community_manager_listed():
    c1 = CommunityFactory(is_listed=True)
    c2 = CommunityFactory(is_listed=False)

    listed_communities = Community.objects.listed()
    assert c1 in listed_communities
    assert c2 not in listed_communities
