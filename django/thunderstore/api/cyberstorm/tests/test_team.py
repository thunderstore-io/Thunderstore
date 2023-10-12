import pytest
from rest_framework.test import APIClient

from thunderstore.account.factories import ServiceAccountFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models.team import Team


@pytest.mark.django_db
def test_team_detail_api_view__for_active_team__returns_data(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(f"/api/cyberstorm/team/{team.name}/")
    result = response.json()

    assert response.status_code == 200
    assert team.name == result["name"]
    assert team.donation_link == result["donation_link"]


@pytest.mark.django_db
def test_team_detail_api_view__for_nonexisting_team__returns_404(api_client: APIClient):
    response = api_client.get("/api/cyberstorm/team/bad/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_detail_api_view__when_fetching_team__is_case_insensitive(
    api_client: APIClient,
):
    TeamFactory(name="RaDTeAm")

    response = api_client.get("/api/cyberstorm/team/radteam/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_detail_api_view__for_inactive_team__returns_404(
    api_client: APIClient,
    team: Team,
):
    team.is_active = False
    team.save()

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_membership_permission__for_unauthenticated_user__returns_401(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(f"/api/cyberstorm/team/{team.name}/members/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_team_membership_permission__for_nonexisting_team__returns_404(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get("/api/cyberstorm/team/bad/members/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_membership_permission__for_inactive_team__returns_404(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    team.is_active = False
    team.save()
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/members/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_membership_permission__for_nonmember__returns_403(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/members/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_team_membership_permission__for_member__returns_200(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/members/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_membership_permission__when_fetching_team__is_case_insensitive(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    team = TeamFactory(name="ThunderGods")
    TeamMemberFactory(team=team, user=user)
    api_client.force_authenticate(user)

    response = api_client.get("/api/cyberstorm/team/thundergods/members/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_members_api_view__for_member__returns_only_real_users(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user, role="member")
    ServiceAccountFactory(owner=team)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/members/")
    result = response.json()

    assert len(result) == 1
    assert result[0]["identifier"] == user.id
    assert result[0]["username"] == user.username
    assert result[0]["avatar"] is None
    assert result[0]["role"] == "member"


@pytest.mark.django_db
def test_team_service_accounts_api_view__for_member__returns_only_service_accounts(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user, role="member")
    sa = ServiceAccountFactory(owner=team)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/service-accounts/")
    result = response.json()

    assert len(result) == 1
    assert result[0]["identifier"] == str(sa.uuid)
    assert result[0]["name"] == sa.user.first_name
    assert result[0]["last_used"] is None
