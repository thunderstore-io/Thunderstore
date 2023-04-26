import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.core.types import UserType


def request_user_info(api_client: APIClient) -> Response:
    return api_client.get(
        "/api/experimental/current-user/",
        HTTP_ACCEPT="application/json",
    )


@pytest.mark.django_db
def test_current_user_info__for_unauthenticated_user__is_empty_structure(
    api_client: APIClient,
) -> None:
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert user_info["username"] is None
    assert user_info["has_subscription"] is False
    assert len(user_info["capabilities"]) == 0
    assert len(user_info["rated_packages"]) == 0
    assert len(user_info["teams"]) == 0


@pytest.mark.django_db
def test_current_user_info__for_authenticated_user__has_proper_values(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user=user)
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert user_info["username"] == "Test"
