from typing import Dict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.models import (
    Community,
    CommunityAggregatedFields,
    CommunitySite,
    PackageListing,
)
from thunderstore.repository.factories import PackageVersionFactory


@pytest.mark.django_db
def test_counts_when_no_communities_exists(api_client: APIClient) -> None:
    # Disable the default Community created by test config.
    Community.objects.update(is_listed=False)
    CommunityAggregatedFields.create_missing()

    for community in Community.objects.all():
        CommunityAggregatedFields.update_for_community(community)

    data = __query_api(api_client)

    assert len(data["communities"]) == 0
    assert data["download_count"] == 0
    assert data["package_count"] == 0


@pytest.mark.django_db
def test_counts_when_no_packages_exists(api_client: APIClient) -> None:
    CommunityAggregatedFields.create_missing()

    for community in Community.objects.all():
        CommunityAggregatedFields.update_for_community(community)

    data = __query_api(api_client)

    assert len(data["communities"]) == 1
    assert data["communities"][0]["download_count"] == 0
    assert data["communities"][0]["package_count"] == 0
    assert data["download_count"] == 0
    assert data["package_count"] == 0


@pytest.mark.django_db
def test_counts_when_packages_have_been_downloaded(api_client: APIClient) -> None:
    site = CommunitySite.objects.get()

    ver1 = PackageVersionFactory(downloads=0)
    ver2 = PackageVersionFactory(downloads=3)
    ver3 = PackageVersionFactory(downloads=5)

    ver3.package.is_deprecated = True  # This should still count.

    PackageListing.objects.create(community=site.community, package=ver1.package)
    PackageListing.objects.create(community=site.community, package=ver2.package)
    PackageListing.objects.create(community=site.community, package=ver3.package)

    CommunityAggregatedFields.create_missing()
    site.community.refresh_from_db()
    CommunityAggregatedFields.update_for_community(site.community)

    data = __query_api(api_client)

    assert len(data["communities"]) == 1

    assert data["communities"][0]["download_count"] == 8
    assert data["communities"][0]["package_count"] == 3

    # Total counts should be the same given the same packages for both communities.
    assert data["download_count"] == 8
    assert data["package_count"] == 3


def __query_api(client: APIClient) -> Dict:
    url = reverse("api:experimental:frontend.frontpage")
    response = client.get(url)
    assert response.status_code == 200
    return response.json()
