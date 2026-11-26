import pytest
from rest_framework.test import APIClient

from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import PackageFactory
from thunderstore.repository.models import Package, PackageRating
from thunderstore.repository.tests.utils import create_version


@pytest.mark.django_db
def test_api_v1_package_metrics(
    user,
    api_client: APIClient,
    active_package: Package,
) -> None:
    active_package.latest.downloads = 200
    active_package.latest.save()

    PackageRating.objects.get_or_create(rater=user, package=active_package)

    assert active_package.rating_score == 1
    assert active_package.downloads == 200

    namespace = active_package.namespace.name
    name = active_package.name
    response = api_client.get(f"/api/v1/package-metrics/{namespace}/{name}/")
    assert response.status_code == 200

    result = response.json()
    assert result["downloads"] == 200
    assert result["rating_score"] == 1
    assert result["latest_version"] == active_package.latest.version_number


@pytest.mark.django_db
def test_api_v1_package_version_metrics(
    user,
    api_client: APIClient,
    active_package: Package,
) -> None:
    active_package.latest.downloads = 200
    active_package.latest.save()

    assert active_package.downloads == 200

    namespace = active_package.namespace.name
    name = active_package.name
    version = active_package.latest.version_number
    response = api_client.get(f"/api/v1/package-metrics/{namespace}/{name}/{version}/")
    assert response.status_code == 200

    result = response.json()
    assert result["downloads"] == 200


@pytest.mark.django_db
def test_api_v1_package_metrics__latest_version_skips_rejected_versions(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    create_version(package, "1.1.0", PackageVersionReviewStatus.unreviewed)
    create_version(package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(
        f"/api/v1/package-metrics/{package.namespace.name}/{package.name}/"
    )

    assert response.status_code == 200
    assert response.json()["latest_version"] == "1.1.0"


@pytest.mark.django_db
def test_api_v1_package_metrics__package_with_only_rejected_versions_returns_404(
    api_client: APIClient,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(
        f"/api/v1/package-metrics/{package.namespace.name}/{package.name}/"
    )

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("review_status", "expected_status"),
    (
        (PackageVersionReviewStatus.approved, 200),
        (PackageVersionReviewStatus.unreviewed, 200),
        (PackageVersionReviewStatus.rejected, 404),
    ),
)
def test_api_v1_package_version_metrics__review_status(
    api_client: APIClient,
    review_status: str,
    expected_status: int,
) -> None:
    package = PackageFactory()
    create_version(package, "1.0.0", PackageVersionReviewStatus.approved)
    create_version(package, "2.0.0", review_status)

    response = api_client.get(
        f"/api/v1/package-metrics/{package.namespace.name}/{package.name}/2.0.0/"
    )

    assert response.status_code == expected_status
