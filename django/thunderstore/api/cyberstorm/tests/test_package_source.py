import pytest
from rest_framework.test import APIClient

from thunderstore.repository.models import Package


def get_package_source_endpoint_url(package: Package, version: str = "") -> str:
    base_url = "/api/cyberstorm/package"

    package_name = package.name
    namespace_id = package.namespace.name
    if not version:
        version = package.version_number

    return f"{base_url}/{namespace_id}/{package_name}/{version}/source/"


@pytest.mark.django_db
def test_package_source_endpoint(api_client: APIClient, active_package: Package):
    url = get_package_source_endpoint_url(active_package)
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_package_not_found(api_client: APIClient, active_package: Package):
    active_package.is_active = False
    active_package.save()

    url = get_package_source_endpoint_url(active_package)
    response = api_client.get(url)

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


@pytest.mark.django_db
def test_package_version_not_found(api_client: APIClient, active_package: Package):
    version = active_package.available_versions.first()
    version.version_number = "2.0.0"
    version.save()

    url = get_package_source_endpoint_url(active_package, version="1.0.0")
    response = api_client.get(url)

    assert response.status_code == 404
    assert response.json() == {"detail": "Package version not found"}


@pytest.mark.django_db
def test_package_source_response_format(api_client: APIClient, active_package: Package):
    url = get_package_source_endpoint_url(active_package)
    response = api_client.get(url)

    expected_result = {
        "is_visible": True,
        "namespace": active_package.namespace.name,
        "package_name": active_package.name,
        "version_number": active_package.version_number,
        "decompilations": [],
    }

    assert response.json() == expected_result
