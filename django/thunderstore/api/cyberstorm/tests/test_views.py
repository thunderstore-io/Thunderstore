import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.models import CommunitySite


@pytest.mark.django_db
def test_views_community(client: APIClient, community_site: CommunitySite):
    response = client.get(
        "/api/cyberstorm/c/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_views_communities(client: APIClient, community_site: CommunitySite):
    response = client.get(
        f"/api/cyberstorm/c/{community_site.community.identifier}/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
