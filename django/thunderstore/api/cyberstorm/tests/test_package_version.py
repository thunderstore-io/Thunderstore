from datetime import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from thunderstore.repository.factories import PackageVersionFactory, TeamMemberFactory
from thunderstore.repository.models.package_version import PackageVersion


def _date_to_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _get_version_url(pv: PackageVersion) -> str:
    return f"/api/cyberstorm/package/{pv.package.namespace.name}/{pv.name}/v/{pv.version_number}/"


# ---------------------------------------------------------------------------
# API view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_package_version_view__returns_info(api_client: APIClient) -> None:
    pv1 = PackageVersionFactory(
        downloads=12,
        website_url="https://thunderstore.io/",
        changelog="some changelog",
    )
    pv2 = PackageVersionFactory()
    pv3 = PackageVersionFactory()
    pv4 = PackageVersionFactory()

    # Set multiple dependencies to ensure only direct dependencies are counted
    pv1.dependencies.set([pv2, pv3])
    # Set a dependency that is not direct
    pv2.dependencies.set([pv4])

    TeamMemberFactory(team=pv1.package.owner, role="owner")
    TeamMemberFactory(team=pv1.package.owner, role="member")

    url = _get_version_url(pv1)
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()

    assert data["datetime_created"] == _date_to_z(pv1.date_created)
    assert data["dependency_count"] == 2
    assert data["description"] == pv1.description
    assert data["download_count"] == pv1.downloads
    assert data["download_url"] == pv1.full_download_url
    assert data["full_version_name"] == pv1.full_version_name
    assert data["icon_url"].startswith("http")
    assert data["name"] == pv1.name
    assert data["namespace"] == pv1.package.namespace.name
    assert data["size"] == pv1.file_size
    assert data["team"]["name"] == pv1.package.owner.name
    assert "members" in data["team"]
    assert data["website_url"] == "https://thunderstore.io/"


@pytest.mark.django_db
def test_package_version_view__serializes_url_correctly(api_client: APIClient) -> None:
    pv = PackageVersionFactory(website_url="https://thunderstore.io/")
    url = _get_version_url(pv)
    assert api_client.get(url).json()["website_url"] == "https://thunderstore.io/"

    pv.website_url = ""
    pv.save(update_fields=("website_url",))
    assert api_client.get(url).json()["website_url"] is None


@pytest.mark.django_db
def test_package_version_view__query_count(api_client: APIClient) -> None:
    pv = PackageVersionFactory()
    deps = [PackageVersionFactory() for _ in range(10)]
    pv.dependencies.set(deps)
    url = _get_version_url(pv)

    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(url)

    assert response.status_code == 200
    # Allow some overhead but ensure it's not exploding
    assert len(ctx.captured_queries) < 20
