import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models import Team, TeamMember


def get_update_team_member_url(team_name: str, team_member: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/member/{team_member}/update/"


def make_request(api_client: APIClient, team_name: str, team_member: str, data: dict):
    return api_client.patch(
        get_update_team_member_url(team_name, team_member),
        json.dumps(data),
        content_type="application/json",
    )


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
    response_json = response.json()

    assert response.status_code == 403
    assert response_json["detail"] == "You do not have permission to edit team members."
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

    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["New role is invalid"]}
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
