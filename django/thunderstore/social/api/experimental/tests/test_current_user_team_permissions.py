import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageFactory, TeamMemberFactory
from thunderstore.repository.models.team import Team


@pytest.mark.django_db
def test_current_user_team_permissions__for_unauthenticated_user__returns_401(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(
        f"/api/experimental/current-user/permissions/team/{team.name}/"
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_current_user_team_permissions__for_nonmember__returns_403(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get(
        f"/api/experimental/current-user/permissions/team/{team.name}/"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_current_user_team_permissions__for_nonexisting_team__returns_404(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get("/api/experimental/current-user/permissions/team/null/")

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("current_user_role", ["owner", "member"])
@pytest.mark.parametrize("team_has_owner", [True, False])
def test_current_user_team_permissions__for_member__returns_can_leave_team(
    current_user_role: str,
    team_has_owner: bool,
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    api_client.force_authenticate(user)
    TeamMemberFactory(team=team, user=user, role=current_user_role)
    if team_has_owner:
        TeamMemberFactory(team=team, role="owner")

    response = api_client.get(
        f"/api/experimental/current-user/permissions/team/{team.name}/"
    )

    assert response.status_code == 200
    expected = current_user_role == "member" or team_has_owner
    actual = response.json()["can_leave_team"]
    assert actual == expected


@pytest.mark.django_db
@pytest.mark.parametrize("current_user_role", ["owner", "member"])
@pytest.mark.parametrize("team_has_packages", [True, False])
def test_current_user_team_permissions__for_member__returns_can_disband_team(
    current_user_role: str,
    team_has_packages: bool,
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    assert team.owned_packages.count() == 0
    api_client.force_authenticate(user)
    TeamMemberFactory(team=team, user=user, role=current_user_role)
    if team_has_packages:
        PackageFactory(owner=team, namespace=team.get_namespace())

    response = api_client.get(
        f"/api/experimental/current-user/permissions/team/{team.name}/"
    )

    assert response.status_code == 200
    expected = current_user_role == "owner" and not team_has_packages
    actual = response.json()["can_disband_team"]
    assert actual == expected
