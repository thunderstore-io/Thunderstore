import pytest
from rest_framework.test import APIClient

from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import Package


def get_package_source_endpoint_url(package: Package, version: str = "") -> str:
    base_url = "/api/cyberstorm/package"

    package_name = package.name
    namespace_id = package.namespace.name
    if not version:
        version = package.version_number

    return f"{base_url}/{namespace_id}/{package_name}/v/{version}/source/"


@pytest.mark.django_db
def test_package_source_endpoint(api_client: APIClient):
    package = PackageFactory(is_active=True)
    PackageVersionFactory(package=package)
    url = get_package_source_endpoint_url(package)
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_package_not_found(api_client: APIClient):
    package = PackageFactory(is_active=False)
    PackageVersionFactory(package=package)

    url = get_package_source_endpoint_url(package)
    response = api_client.get(url)

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


@pytest.mark.django_db
def test_package_version_not_found(api_client: APIClient):
    package = PackageFactory(is_active=True)
    PackageVersionFactory(package=package)
    version = package.available_versions.first()
    version.version_number = "2.0.0"
    version.save()

    url = get_package_source_endpoint_url(package, version="1.0.0")
    response = api_client.get(url)

    assert response.status_code == 404
    assert response.json() == {"detail": "Package version not found"}


@pytest.mark.django_db
def test_package_source_response_format(api_client: APIClient):
    package = PackageFactory(is_active=True)
    PackageVersionFactory(package=package)
    url = get_package_source_endpoint_url(package)
    response = api_client.get(url)

    expected_result = {
        "is_visible": True,
        "namespace": package.namespace.name,
        "package_name": package.name,
        "version_number": package.version_number,
        "decompilations": [],
    }

    assert response.json() == expected_result
