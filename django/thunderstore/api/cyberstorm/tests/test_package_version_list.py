import pytest
from rest_framework.test import APIClient

from thunderstore.repository.factories import PackageVersionFactory
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
