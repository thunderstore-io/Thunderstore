import datetime

import pytest
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.account.models.user_flag import UserFlag, UserFlagMembership
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
    assert user_info["subscription"]["expires"] is None
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
    assert type(user_info["subscription"]) == dict
    assert "expires" in user_info["subscription"]
    assert user_info["subscription"]["expires"] is None

    beta_access_flag = UserFlag.objects.create(
        name="Cyberstorm Beta",
        description="Cyberstorm Beta Access",
        app_label="social",
        identifier="cyberstorm_beta_access",
    )
    now = timezone.now()
    UserFlagMembership.objects.create(
        user=user,
        flag=beta_access_flag,
        datetime_valid_from=now - datetime.timedelta(minutes=5),
    )

    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert user_info["username"] == "Test"
    assert type(user_info["subscription"]) == dict
    assert "expires" in user_info["subscription"]
    expiry_datetime = datetime.datetime.fromisoformat(
        user_info["subscription"]["expires"].replace("Z", "+00:00")
    )
    assert expiry_datetime > now + datetime.timedelta(
        days=27
    ) and expiry_datetime < now + datetime.timedelta(days=29)
