import json

import pytest
from rest_framework.test import APIClient

from thunderstore.community.models.community_site import CommunitySite
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.repository.api.v1.tasks import update_api_v1_caches


@pytest.mark.django_db
def test_api_v1(
    api_client: APIClient,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
):
    update_api_v1_caches()
    response = api_client.get(
        f"/c/{community_site.community.identifier}/api/v1/package/"
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name

    # TODO: Enable once detail views have been re-enabled
    # uuid = result[0]["uuid4"]
    # response = api_client.get(
    #     f"/api/v1/package/{uuid}/",
    # )
    # assert response.status_code == 200
    # assert response.json() == result[0]


@pytest.mark.django_db
def test_api_v1_rate_package(
    api_client: APIClient,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
):
    uuid = active_package_listing.package.uuid4
    user = UserFactory.create()
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "rated"
    assert result["score"] == 1

    response = api_client.post(
        f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/rate/",
        json.dumps({"target_state": "unrated"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "unrated"
    assert result["score"] == 0


@pytest.mark.django_db
def test_api_v1_rate_package_permission_denied(
    api_client: APIClient,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
):
    uuid = active_package_listing.package.uuid4
    response = api_client.post(
        f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Authentication credentials were not provided."
