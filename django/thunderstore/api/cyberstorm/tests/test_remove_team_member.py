import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models.team import Team, TeamMember, TeamMemberRole


def get_remove_team_member_url(team_name: str, team_member: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/member/{team_member}/remove/"


def make_request(api_client: APIClient, team_name: str, team_member: str):
    return api_client.delete(
        get_remove_team_member_url(team_name, team_member),
        content_type="application/json",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_remove_team_member_user_roles(user_type, api_client, team_member):
    user = TestUserTypes.get_user_by_type(user_type)
    team_member_pk = team_member.pk

    user_type_result = {
        TestUserTypes.no_user: 401,
        TestUserTypes.unauthenticated: 401,
        TestUserTypes.regular_user: 204,
        TestUserTypes.deactivated_user: 403,
        TestUserTypes.service_account: 403,
        TestUserTypes.site_admin: 204,
        TestUserTypes.superuser: 204,
    }

    if not user_type in [TestUserTypes.no_user, TestUserTypes.unauthenticated]:
        team_member.team.add_member(user=user, role=TeamMemberRole.owner)
        api_client.force_authenticate(user)

    response = make_request(
        api_client, team_member.team.name, team_member.user.username
    )

    assert response.status_code == user_type_result[user_type]

    if response.status_code == 204:
        assert not TeamMember.objects.filter(pk=team_member_pk).exists()
    else:
        assert TeamMember.objects.filter(pk=team_member_pk).exists()


@pytest.mark.django_db
def test_remove_team_member_success(api_client: APIClient, user: UserType, team: Team):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    just_a_member = TeamMemberFactory(team=team, role="member")
    response = make_request(api_client, team.name, just_a_member.user.username)

    assert response.status_code == 204


@pytest.mark.django_db
def test_remove_member_fail_because_user_is_not_a_member_in_team(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    another_team = TeamFactory()
    member_in_another_team = TeamMemberFactory(team=another_team, role="owner")

    response = make_request(api_client, team.name, member_in_another_team.user.username)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_remove_fail_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = make_request(api_client, "nonexistent", user.username)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_remove_fail_user_is_not_authenticated(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    just_a_member = TeamMemberFactory(team=team, role="member")

    response = make_request(api_client, team.name, just_a_member.user.username)
    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == 401
    assert response.json() == expected_response


@pytest.mark.django_db
def test_remove_fail_no_permission_to_access_team(
    api_client: APIClient, user: UserType, team: Team
):
    api_client.force_authenticate(user)
    owner = TeamMemberFactory(team=team, role="owner")

    response = make_request(api_client, team.name, owner.user.username)
    expected_response = {"non_field_errors": ["Must be a member to access team"]}

    assert response.status_code == 403
    assert response.json() == expected_response


@pytest.mark.django_db
def test_remove_fail_last_owner(api_client: APIClient, user: UserType, team: Team):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    response = make_request(api_client, team.name, user.username)
    expected_response = {"non_field_errors": ["Cannot remove last owner from team"]}

    assert response.status_code == 400
    assert response.json() == expected_response
