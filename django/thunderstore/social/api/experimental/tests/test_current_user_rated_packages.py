import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageRating


@pytest.mark.django_db
def test_api_experimental_current_user_rated_packages__valid_user(
    api_client: APIClient, active_package: Package, user: UserType
):
    PackageRating.objects.create(rater=user, package=active_package)
    api_client.force_authenticate(user)
    response = api_client.get(
        "/api/experimental/current-user/rated-packages/",
        content_type="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["rated_packages"] == [active_package.full_package_name]


@pytest.mark.django_db
def test_api_experimental_current_user_rated_packages__invalid_user(
    api_client: APIClient,
):
    response = api_client.get(
        "/api/experimental/current-user/rated-packages/",
        content_type="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["rated_packages"] == []
