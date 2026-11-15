from typing import Optional

import pytest
from rest_framework.test import APIClient

from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion


def create_version(
    package: Package,
    version_number: str,
    review_status: str,
    is_active: bool = True,
) -> PackageVersion:
    return PackageVersionFactory(
        package=package,
        name=package.name,
        version_number=version_number,
        review_status=review_status,
        is_active=is_active,
    )


def package_url(package: Package, version: Optional[str] = None) -> str:
    url = f"/api/experimental/package/{package.owner.name}/{package.name}/"
    return f"{url}{version}/" if version else url


@pytest.mark.django_db
def test_package_list__package_with_only_rejected_versions_is_excluded(
    api_client: APIClient,
) -> None:
    visible = PackageFactory()
    create_version(visible, "1.0.0", PackageVersionReviewStatus.unreviewed)
    rejected = PackageFactory()
    create_version(rejected, "1.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get("/api/experimental/package/")

    assert response.status_code == 200
    assert [p["full_name"] for p in response.json()["results"]] == [
        visible.full_package_name
    ]


@pytest.mark.django_db
def test_package_list__latest_skips_rejected_versions(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get("/api/experimental/package/")

    assert response.status_code == 200
    [result] = response.json()["results"]
    assert result["latest"]["version_number"] == "1.0.0"


@pytest.mark.django_db
def test_package_detail__package_with_only_rejected_versions_returns_404(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.rejected)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(package_url(package))

    assert response.status_code == 404


@pytest.mark.django_db
def test_package_detail__package_whose_non_rejected_versions_are_inactive_returns_404(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(
        package, "1.0.0", PackageVersionReviewStatus.approved, is_active=False
    )
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(package_url(package))

    assert response.status_code == 404


@pytest.mark.django_db
def test_package_detail__latest_is_newest_non_rejected_version(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    create_version(package, "1.1.0", PackageVersionReviewStatus.unreviewed)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(package_url(package))

    assert response.status_code == 200
    assert response.json()["latest"]["version_number"] == "1.1.0"


@pytest.mark.django_db
def test_package_detail__rejecting_latest_version_falls_back_to_previous(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    newest = create_version(package, "2.0.0", PackageVersionReviewStatus.unreviewed)

    newest.reject(agent=None, is_system=True)
    response = api_client.get(package_url(package))

    assert response.status_code == 200
    assert response.json()["latest"]["version_number"] == "1.0.0"


@pytest.mark.django_db
def test_package_detail__rejecting_last_visible_version_returns_404(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    version = create_version(package, "1.0.0", PackageVersionReviewStatus.approved)

    version.reject(agent=None, is_system=True)
    response = api_client.get(package_url(package))

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", ("", "changelog/", "readme/"))
def test_package_version__rejected_version_returns_404(
    api_client: APIClient,
    suffix: str,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(package_url(package, "2.0.0") + suffix)

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", ("", "changelog/", "readme/"))
@pytest.mark.parametrize(
    "review_status",
    (PackageVersionReviewStatus.approved, PackageVersionReviewStatus.unreviewed),
)
def test_package_version__non_rejected_version_next_to_rejected_one_is_returned(
    api_client: APIClient,
    suffix: str,
    review_status: str,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", review_status)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(package_url(package, "1.0.0") + suffix)

    assert response.status_code == 200
