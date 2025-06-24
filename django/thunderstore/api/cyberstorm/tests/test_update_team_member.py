import json

import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models import Team, TeamMember
from thunderstore.repository.models.team import TeamMemberRole


def get_update_team_member_url(team_name: str, team_member: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/member/{team_member}/update/"


def make_request(api_client: APIClient, team_name: str, team_member: str, data: dict):
    return api_client.patch(
        get_update_team_member_url(team_name, team_member),
        json.dumps(data),
        content_type="application/json",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("user_role", TestUserTypes.options())
def test_update_team_member_user_roles(
    user_role: str,
    api_client: APIClient,
    team_member: TeamMember,
):
    user = TestUserTypes.get_user_by_type(user_role)
    team = team_member.team

    if user_role not in TestUserTypes.fake_users():
        team.add_member(user=user, role=TeamMemberRole.owner)
        api_client.force_authenticate(user)

    expected_status_code = {
        TestUserTypes.no_user: 401,
        TestUserTypes.unauthenticated: 401,
        TestUserTypes.regular_user: 200,
        TestUserTypes.deactivated_user: 403,
        TestUserTypes.service_account: 403,
        TestUserTypes.site_admin: 200,
        TestUserTypes.superuser: 200,
    }

    response = make_request(
        api_client,
        team.name,
        team_member.user.username,
        {"role": "owner"},
    )

    assert response.status_code == expected_status_code[user_role]

    if response.status_code == 200:
        assert TeamMember.objects.get(pk=team_member.pk).role == TeamMemberRole.owner


@pytest.mark.django_db
def test_update_team_member_success(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    just_a_member = TeamMemberFactory(team=team, role="owner")

    data = {"role": "member"}
    team_member = just_a_member.user.username
    response = make_request(api_client, team.name, team_member, data)
    response_json = response.json()

    assert response.status_code == 200
    assert response_json["team_name"] == team.name
    assert response_json["username"] == just_a_member.user.username
    assert response_json["role"] == "member"
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "member"


@pytest.mark.django_db
def test_update_team_member_fail_user_not_in_team(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    another_team = TeamFactory()
    member_in_another_team = TeamMemberFactory(team=another_team, role="owner")

    data = {"role": "member"}
    team_member = member_in_another_team.user.username
    response = make_request(api_client, team.name, team_member, data)
    response_json = response.json()

    assert response.status_code == 404
    assert response_json["detail"] == "Not found."
    assert TeamMember.objects.get(pk=member_in_another_team.pk).role == "owner"


@pytest.mark.django_db
def test_update_team_member_fails_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    data = {"role": "member"}
    response = make_request(api_client, "GhostTeam", user.username, data)
    response_json = response.json()

    assert response.status_code == 404
    assert response_json["detail"] == "Not found."


@pytest.mark.django_db
def test_update_team_member_fails_user_not_authenticated(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    just_a_member = TeamMemberFactory(team=team, role="owner")

    data = {"role": "member"}
    team_member = just_a_member.user.username
    response = make_request(api_client, team.name, team_member, data)
    response_json = response.json()

    assert response.status_code == 401
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "owner"


@pytest.mark.django_db
def test_update_team_member_fails_user_can_not_manage_members(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="member")
    api_client.force_authenticate(user)
    just_a_member = TeamMemberFactory(team=team, role="member")

    data = {"role": "member"}
    team_member = just_a_member.user.username
    response = make_request(api_client, team.name, team_member, data)
    expected_response = {
        "non_field_errors": ["Must be an owner to manage team members"]
    }

    assert response.status_code == 403
    assert response.json() == expected_response
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "member"


@pytest.mark.django_db
def test_update_team_member_fails_invalid_role(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    just_a_member = TeamMemberFactory(team=team, role="owner")

    data = {"role": "invalid_role"}
    team_member = just_a_member.user.username
    response = make_request(api_client, team.name, team_member, data)
    expected_response = {"role": ['"invalid_role" is not a valid choice.']}

    assert response.status_code == 400
    assert response.json() == expected_response
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "owner"


@pytest.mark.django_db
def test_update_team_members_fails_last_owner(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    last_owner = TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    data = {"role": "member"}
    team_member = last_owner.user.username
    response = make_request(api_client, team.name, team_member, data)

    assert response.status_code == 400
    assert TeamMember.objects.get(pk=last_owner.pk).role == "owner"
