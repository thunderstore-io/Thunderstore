import pytest
from rest_framework.test import APIClient

from thunderstore.repository.models import Package, PackageRating


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


@pytest.mark.django_db
def test_api_v1_package_version_metrics(
    user,
    api_client: APIClient,
    active_package: Package,
) -> None:
    active_package.latest.downloads = 200
    active_package.latest.save()

    assert active_package.latest.downloads == 200

    namespace = active_package.namespace.name
    name = active_package.name
    version = active_package.latest.version_number
    response = api_client.get(f"/api/v1/package-metrics/{namespace}/{name}/{version}/")
    assert response.status_code == 200

    result = response.json()
    assert result["downloads"] == 200
