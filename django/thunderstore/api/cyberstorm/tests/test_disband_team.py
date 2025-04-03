import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.repository.models.team import Team


def get_disband_team_url(team_name: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/disband/"


def make_request(api_client: APIClient, team_name: str):
    return api_client.delete(
        get_disband_team_url(team_name),
        content_type="application/json",
    )


@pytest.mark.django_db
def test_disband_team_success(api_client: APIClient, user: UserType, team: Team):
    TeamMemberFactory(team=team, user=user, role="owner")
    assert Team.objects.filter(name=team.name).count() == 1
    api_client.force_authenticate(user)
    response = make_request(api_client, team.name)
    assert response.status_code == 204
    assert Team.objects.filter(name=team.name).count() == 0


@pytest.mark.django_db
def test_disband_team_fail_because_team_doesnt_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)
    response = make_request(api_client, "nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_disband_team__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    team: Team,
):
    assert Team.objects.filter(name=team.name).count() == 1
    response = make_request(api_client, team.name)
    expected_response = {"detail": "Authentication credentials were not provided."}
    assert response.status_code == 401
    assert response.json() == expected_response
    assert Team.objects.filter(name=team.name).count() == 1


@pytest.mark.django_db
def test_disband_team_fail_because_user_is_not_owner(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="member")
    api_client.force_authenticate(user)
    response = make_request(api_client, team.name)
    expected_response = {"non_field_errors": ["User cannot disband this team"]}
    assert response.status_code == 400
    assert response.json() == expected_response


@pytest.mark.django_db
def test_disband_team_fail_because_user_cannot_access_team(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    api_client.force_authenticate(user)
    response = make_request(api_client, team.name)
    expected_response = {"detail": "You do not have permission to access this team."}
    assert response.status_code == 403
    assert response.json() == expected_response
