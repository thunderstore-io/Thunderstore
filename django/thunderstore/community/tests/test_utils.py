import pytest

from thunderstore.community.models import Community
from thunderstore.community.utils import (
    get_community_for_request,
    get_default_community,
)


@pytest.mark.django_db
def test_get_default_community_returns_none_when_missing():
    Community.objects.filter(identifier="riskofrain2").delete()
    assert get_default_community() is None


@pytest.mark.django_db
def test_get_default_community_returns_community_when_present():
    community, _ = Community.objects.get_or_create(
        identifier="riskofrain2", defaults={"name": "Risk of Rain 2"}
    )
    result = get_default_community()
    assert result == community


@pytest.mark.django_db
def test_get_community_for_request_returns_existing_community(rf):
    community, _ = Community.objects.get_or_create(
        identifier="riskofrain2", defaults={"name": "Risk of Rain 2"}
    )
    request = rf.get("/")
    result = get_community_for_request(request)
    assert result == community
    assert Community.objects.filter(identifier="riskofrain2").count() == 1


@pytest.mark.django_db
def test_get_community_for_request_creates_community_when_missing(rf):
    Community.objects.filter(identifier="riskofrain2").delete()
    request = rf.get("/")
    result = get_community_for_request(request)
    assert result is not None
    assert result.identifier == "riskofrain2"
    assert result.name == "Risk of Rain 2"
    assert Community.objects.filter(identifier="riskofrain2").count() == 1
