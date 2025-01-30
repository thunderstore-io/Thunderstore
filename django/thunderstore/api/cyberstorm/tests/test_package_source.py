import pytest
from rest_framework.test import APIClient

from thunderstore.repository.models import Package
from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageVersion


def get_package_source_endpoint_url(package: Package) -> str:
    base_url = "/api/cyberstorm/package"

    package_name = package.name
    namespace_id = package.namespace.name
    version = package.version_number  # Grab latest version for testing

    return f"{base_url}/{namespace_id}/{package_name}/{version}/source/"


@pytest.mark.django_db
def test_package_source_endpoint(api_client: APIClient, active_package: Package):
    url = get_package_source_endpoint_url(active_package)
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_package_source_response_format(api_client: APIClient, active_package: Package):
    url = get_package_source_endpoint_url(active_package)
    response = api_client.get(url)

    assert "is_visible" in response.json()
    assert "decompilations" in response.json()
