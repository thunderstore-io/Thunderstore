import datetime
from typing import Optional

import pytest
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient
from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.account.factories import ServiceAccountFactory
from thunderstore.account.models.user_flag import UserFlag, UserFlagMembership
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.repository.models.team import TeamMemberRole


def request_user_info(api_client: APIClient) -> Response:
    return api_client.get(
        "/api/experimental/current-user/",
        HTTP_ACCEPT="application/json",
    )


def request_user_info_v1(api_client: APIClient) -> Response:
    url = "/api/v1/current-user/info/"
    return api_client.get(url, HTTP_ACCEPT="application/json")


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
    assert len(user_info["connections"]) == 0
    assert len(user_info["rated_packages"]) == 0
    assert len(user_info["teams"]) == 0


@pytest.mark.django_db
def test_current_user_info__for_authenticated_user__has_basic_values(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user=user)
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert user_info["username"] == "Test"
    assert type(user_info["capabilities"]) == list
    assert type(user_info["rated_packages"]) == list


@pytest.mark.django_db
def test_current_user_info__for_subscriber__has_subscription_expiration(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user=user)
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

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

    assert type(user_info["subscription"]) == dict
    assert "expires" in user_info["subscription"]
    expiry_datetime = datetime.datetime.fromisoformat(
        user_info["subscription"]["expires"].replace("Z", "+00:00"),
    )
    assert now + datetime.timedelta(days=27) < expiry_datetime
    assert expiry_datetime < now + datetime.timedelta(days=29)


@pytest.mark.django_db
def test_current_user_info__for_oauth_user__has_connections(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user=user)
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert type(user_info["connections"]) == list
    assert len(user_info["connections"]) == 0

    UserSocialAuth.objects.bulk_create(
        [
            UserSocialAuth(
                user=user,
                provider="discord",
                uid="d123",
                extra_data={"username": "discord_user"},
            ),
            UserSocialAuth(
                user=user,
                provider="github",
                uid="gh123",
                extra_data={"login": "gh_user", "avatar_url": "gh_url"},
            ),
            UserSocialAuth(
                user=user,
                provider="overwolf",
                uid="ow123",
                extra_data={"nickname": "ow_user", "avatar": "ow_url"},
            ),
            UserSocialAuth(
                user=user,
                provider="unknown",
                uid="unk123",
                extra_data={},
            ),
        ],
    )

    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert type(user_info["connections"]) == list
    assert len(user_info["connections"]) == 4

    discord = next(c for c in user_info["connections"] if c["provider"] == "discord")
    assert discord["username"] == "discord_user"
    assert discord["avatar"] is None

    github = next(c for c in user_info["connections"] if c["provider"] == "github")
    assert github["username"] == "gh_user"
    assert github["avatar"] == "gh_url"

    overwolf = next(c for c in user_info["connections"] if c["provider"] == "overwolf")
    assert overwolf["username"] == "ow_user"
    assert overwolf["avatar"] == "ow_url"

    unknown = next(c for c in user_info["connections"] if c["provider"] == "unknown")
    assert unknown["username"] is None
    assert unknown["avatar"] is None


@pytest.mark.django_db
def test_current_user_info__for_team_member__has_teams(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user=user)
    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert type(user_info["teams"]) == list
    assert len(user_info["teams"]) == 0

    # First team contains only the user, second team has another member
    # and a service account.
    member1 = TeamMemberFactory.create(user=user, role=TeamMemberRole.owner)
    member2 = TeamMemberFactory.create(user=user, role=TeamMemberRole.member)
    TeamMemberFactory.create(team=member2.team)
    sa = ServiceAccountFactory(owner=member2.team)
    TeamMemberFactory(user=sa.user, team=member2.team)

    response = request_user_info(api_client)

    assert response.status_code == 200

    user_info = response.json()

    assert type(user_info["teams"]) == list
    assert len(user_info["teams"]) == 2
    assert type(user_info["teams_full"]) == list
    assert len(user_info["teams_full"]) == 2

    assert user_info["teams"] == [t["name"] for t in user_info["teams_full"]]

    team1 = next(t for t in user_info["teams_full"] if t["name"] == member1.team.name)
    assert team1["role"] == TeamMemberRole.owner
    assert team1["member_count"] == 1

    team2 = next(t for t in user_info["teams_full"] if t["name"] == member2.team.name)
    assert team2["role"] == TeamMemberRole.member
    assert team2["member_count"] == 2  # ServiceAccounts do not count.


def _run_current_user_is_staff_test(
    api_client: APIClient,
    user: UserType,
    is_authorized: bool,
    is_staff: bool,
    expected_status: Optional[bool],
    is_v1_api: bool,
):
    user.is_staff = is_staff

    if is_authorized:
        api_client.force_authenticate(user=user)

    if is_v1_api:
        response = request_user_info_v1(api_client)
    else:
        # Experimental API
        response = request_user_info(api_client)

    assert response.status_code == 200
    assert response.json()["is_staff"] == expected_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_authorized", "is_staff", "expected_status"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_current_user_is_staff_experimental_api(
    api_client: APIClient,
    user: UserType,
    is_authorized: bool,
    is_staff: bool,
    expected_status: Optional[bool],
):
    _run_current_user_is_staff_test(
        api_client, user, is_authorized, is_staff, expected_status, False
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_authorized", "is_staff", "expected_status"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_current_user_is_staff_v1_api(
    api_client: APIClient,
    user: UserType,
    is_authorized: bool,
    is_staff: bool,
    expected_status: Optional[bool],
):
    _run_current_user_is_staff_test(
        api_client,
        user,
        is_authorized,
        is_staff,
        expected_status,
        True,
    )
