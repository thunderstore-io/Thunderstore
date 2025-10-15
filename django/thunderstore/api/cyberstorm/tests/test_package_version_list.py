from typing import Optional

import pytest
from rest_framework.test import APIClient

from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_package_version_list_api_view__returns_error_for_inactive_package(
    api_client: APIClient,
    package: Package,
) -> None:
    package.is_active = False
    package.save()

    response = api_client.get(
        f"/api/cyberstorm/package/{package.namespace}/{package.name}/versions/",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_package_version_list_api_view__does_not_return_inactive_versions(
    api_client: APIClient,
) -> None:
    inactive = PackageVersionFactory(is_active=False)

    response = api_client.get(
        f"/api/cyberstorm/package/{inactive.package.namespace}/{inactive.package.name}/versions/",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_package_version_list_api_view__returns_versions(
    api_client: APIClient,
) -> None:
    expected = PackageVersionFactory()

    response = api_client.get(
        f"/api/cyberstorm/package/{expected.package.namespace}/{expected.package.name}/versions/",
    )
    actual = response.json()

    assert len(actual) == 1
    assert actual[0]["version_number"] == expected.version_number


@pytest.mark.django_db
@pytest.mark.parametrize(
    "version, should_raise_404",
    [
        ("1.0.0", False),
        ("latest", True),
        ("hello", True),
        ("world", True),
        (None, True),
        ("", True),
    ],
)
def test_package_version_dependencies_list(
    api_client: APIClient,
    version: Optional[str],
    should_raise_404: bool,
) -> None:
    """ "Test the PackageVersionDependenciesListAPIView with different version inputs."""

    dependency_count = 1

    package = PackageFactory(name="TestPackage")
    PackageVersionFactory(package=package)

    target_dependencies = [PackageVersionFactory() for _ in range(dependency_count)]
    package.latest.dependencies.set([dep.id for dep in target_dependencies])

    namespace = package.namespace.name
    package_name = package.name

    url = (
        f"/api/cyberstorm/package/{namespace}/{package_name}/v/{version}/dependencies/"
    )
    response = api_client.get(url)

    if should_raise_404:
        assert response.status_code == 404
    else:
        assert response.status_code == 200
        assert response.json()["count"] == dependency_count


@pytest.mark.django_db
def test_package_version_dependencies_list_response(api_client: APIClient) -> None:
    """Test the response structure of the PackageVersionDependenciesListAPIView."""

    dependency_count = 1

    package = PackageFactory(name="TestPackage")
    PackageVersionFactory(package=package)

    target_dependencies = [PackageVersionFactory() for _ in range(dependency_count)]
    package.latest.dependencies.set([dep.id for dep in target_dependencies])

    namespace = package.namespace.name
    package_name = package.name
    version_number = package.latest.version_number

    url = f"/api/cyberstorm/package/{namespace}/{package_name}/v/{version_number}/dependencies/"
    response = api_client.get(url)

    target_version = target_dependencies[0]
    expected_data = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "description": target_version.description,
                "icon_url": target_version.icon.url,
                "is_active": True,
                "name": target_version.name,
                "namespace": target_version.package.namespace.name,
                "version_number": target_version.version_number,
                "is_removed": False,
            }
        ],
    }

    assert response.status_code == 200
    assert response.json() == expected_data


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_active, is_removed",
    [
        (False, True),
        (True, False),
    ],
)
def test_package_version_dependencies_list_version_is_active(
    api_client: APIClient,
    is_active: bool,
    is_removed: bool,
) -> None:
    """Test the is_removed field in the PackageVersionDependenciesListAPIView."""

    package = PackageFactory(name="TestPackage")
    package_version = PackageVersionFactory(package=package)

    dependency = PackageVersionFactory(is_active=is_active)
    package_version.dependencies.set([dependency.id])

    namespace = package.namespace.name
    package_name = package.name
    version_number = package.latest.version_number

    url = f"/api/cyberstorm/package/{namespace}/{package_name}/v/{version_number}/dependencies/"
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.json()["results"][0]["is_removed"] == is_removed
    assert response.json()["results"][0]["is_active"] == is_active
