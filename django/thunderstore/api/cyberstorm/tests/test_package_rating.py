import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package


def get_package_rating_url(package: Package) -> str:
    namespace_id = package.namespace.name
    package_name = package.name
    return f"/api/cyberstorm/package/{namespace_id}/{package_name}/rate/"


@pytest.mark.django_db
def test_rate_package(
    api_client: APIClient,
    active_package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        get_package_rating_url(active_package),
        data=json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "state": "rated",
        "score": 1,
    }

    response = api_client.post(
        get_package_rating_url(active_package),
        data=json.dumps({"target_state": "unrated"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "state": "unrated",
        "score": 0,
    }


@pytest.mark.django_db
def test_rate_package_404(api_client: APIClient, user: UserType) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/cyberstorm/package/BAD/BAD/rate/",
        data=json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_rate_package_401(
    api_client: APIClient,
    active_package: Package,
) -> None:
    response = api_client.post(
        get_package_rating_url(active_package),
        data=json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided.",
    }


@pytest.mark.django_db
def test_rate_package_required_field(
    api_client: APIClient,
    active_package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        get_package_rating_url(active_package),
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "target_state": ["This field is required."],
    }


@pytest.mark.django_db
def test_rate_package_invalid_target_state(
    api_client: APIClient,
    active_package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        get_package_rating_url(active_package),
        data=json.dumps({"target_state": "invalid_state"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Invalid target_state"]}
