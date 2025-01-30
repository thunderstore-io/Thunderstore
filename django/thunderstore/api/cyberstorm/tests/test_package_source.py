import pytest
from rest_framework.test import APIClient

from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType


def get_package_source_endpoint_url(package_listing: PackageListing) -> str:
    base_url = "/api/cyberstorm/listing"

    package_name = package_listing.package.name
    namespace_id = package_listing.package.namespace.name
    community_id = package_listing.community.identifier

    return f"{base_url}/{community_id}/{namespace_id}/{package_name}/source/"


@pytest.mark.django_db
def test_package_source_endpoint(
    api_client: APIClient, active_package_listing: PackageListing
) -> None:

    url = get_package_source_endpoint_url(active_package_listing)
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_package_source_response_format(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    url = get_package_source_endpoint_url(active_package_listing)
    response = api_client.get(url)

    assert response.status_code == 200
    assert "is_visible" in response.json()
    assert "decompilations" in response.json()
