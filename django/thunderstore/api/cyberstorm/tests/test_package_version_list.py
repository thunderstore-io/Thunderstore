import pytest
from rest_framework.test import APIClient

from thunderstore.permissions.factories import VisibilityFlagsFactory
from thunderstore.repository.consts import PackageVersionReviewStatus
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


@pytest.mark.django_db
def test_only_visible_versions_are_returned(
    api_client: APIClient,
) -> None:
    version1 = PackageVersionFactory(version_number="1.0.0")
    version1.review_status = PackageVersionReviewStatus.approved
    version1.save()

    version2 = PackageVersionFactory(package=version1.package, version_number="2.0.0")
    version2.review_status = PackageVersionReviewStatus.rejected
    version2.save()

    assert version1.visibility.public_list is True
    assert version2.visibility.public_list is False

    response = api_client.get(
        f"/api/cyberstorm/package/{version1.package.namespace}/{version1.package.name}/versions/",
    )
    actual = response.json()

    assert len(actual) == 1
    assert actual[0]["version_number"] == version1.version_number
