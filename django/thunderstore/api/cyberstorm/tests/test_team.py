import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.account.factories import ServiceAccountFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models.team import Team, TeamMember

User = get_user_model()


@pytest.mark.django_db
def test_team_api_view__for_active_team__returns_data(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(f"/api/cyberstorm/team/{team.name}/")
    result = response.json()

    assert response.status_code == 200
    assert team.name == result["name"]
    assert team.donation_link == result["donation_link"]


@pytest.mark.django_db
def test_team_api_view__for_nonexisting_team__returns_404(api_client: APIClient):
    response = api_client.get("/api/cyberstorm/team/bad/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_api_view__when_fetching_team__is_case_insensitive(
    api_client: APIClient,
):
    TeamFactory(name="RaDTeAm")

    response = api_client.get("/api/cyberstorm/team/radteam/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_api_view__for_inactive_team__returns_404(
    api_client: APIClient,
    team: Team,
):
    team.is_active = False
    team.save()

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_edit__when_editing_donation_link__succeeds(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    new_donation_link = "https://example.com"

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/edit/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["donation_link"] == new_donation_link
    assert Team.objects.get(pk=team.pk).donation_link == new_donation_link


@pytest.mark.django_db
def test_team_edit__when_editing_donation_link__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    team: Team,
):
    new_donation_link = "https://example.com"

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/edit/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert Team.objects.get(pk=team.pk).donation_link == None


@pytest.mark.django_db
def test_team_edit__when_editing_donation_link__fails_because_serializer_validators_check_fails(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    new_bad_donation_link = "example.com"

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/edit/",
        json.dumps({"donation_link": new_bad_donation_link}),
        content_type="application/json",
    )

    assert response.status_code == 400
    response_json = response.json()
    assert "Enter a valid URL." in response_json["donation_link"]


@pytest.mark.django_db
def test_team_membership_permission__for_no_user__returns_403(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_team_membership_permission__for_nonexisting_team__returns_404(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get("/api/cyberstorm/team/bad/member/")

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

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_membership_permission__for_nonmember__returns_403(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_team_membership_permission__for_member__returns_200(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_membership_permission__when_fetching_team__is_case_insensitive(
    api_client: APIClient,
    user: UserType,
):
    team = TeamFactory(name="ThunderGods")
    TeamMemberFactory(team=team, user=user)
    api_client.force_authenticate(user)

    response = api_client.get("/api/cyberstorm/team/thundergods/member/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_team_members_edit__when_changing_role__succeeds(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    just_a_member = TeamMemberFactory(team=team, role="owner")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/edit/",
        json.dumps({"username": just_a_member.user.username, "role": "member"}),
        content_type="application/json",
    )

    response_json = response.json()
    assert response.status_code == 200
    assert response_json["team_name"] == team.name
    assert response_json["username"] == just_a_member.user.username
    assert response_json["role"] == "member"
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "member"


@pytest.mark.django_db
def test_team_members_edit__when_changing_role__fails_because_user_is_not_in_the_team(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    another_team = TeamFactory()
    member_in_another_team = TeamMemberFactory(team=another_team, role="owner")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/edit/",
        json.dumps(
            {"username": member_in_another_team.user.username, "role": "member"}
        ),
        content_type="application/json",
    )

    assert response.status_code == 404
    response_json = response.json()
    assert response_json["detail"] == "Not found."


@pytest.mark.django_db
def test_team_members_edit__when_changing_role__fails_because_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/cyberstorm/team/GhostTeam/members/edit/",
        json.dumps({"username": user.username, "role": "member"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    response_json = response.json()
    assert response_json["detail"] == "Not found."


@pytest.mark.django_db
def test_team_members_edit__when_changing_role__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    just_a_member = TeamMemberFactory(team=team, role="owner")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/edit/",
        json.dumps({"username": just_a_member.user.username, "role": "member"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert TeamMember.objects.get(pk=just_a_member.pk).role == "owner"


@pytest.mark.django_db
def test_team_member_list_api_view__for_member__returns_only_real_users(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user, role="member")
    ServiceAccountFactory(owner=team)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")
    result = response.json()

    assert len(result) == 1
    assert result[0]["identifier"] == user.id
    assert result[0]["username"] == user.username
    assert result[0]["avatar"] is None
    assert result[0]["role"] == "member"


@pytest.mark.django_db
def test_team_member_list_api_view__for_member__sorts_results(
    api_client: APIClient,
    team: Team,
):
    alice = User.objects.create(username="Alice")
    bob = User.objects.create(username="Bob")
    erin = User.objects.create(username="Erin")
    dan = User.objects.create(username="Dan")
    charlie = User.objects.create(username="Charlie")
    TeamMemberFactory(team=team, user=alice, role="member")
    TeamMemberFactory(team=team, user=bob, role="owner")
    TeamMemberFactory(team=team, user=erin, role="member")
    TeamMemberFactory(team=team, user=dan, role="owner")
    TeamMemberFactory(team=team, user=charlie, role="member")
    api_client.force_authenticate(alice)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/member/")
    result = response.json()

    # Owners alphabetically, then members alphabetically.
    assert len(result) == 5
    assert result[0]["username"] == bob.username
    assert result[1]["username"] == dan.username
    assert result[2]["username"] == alice.username
    assert result[3]["username"] == charlie.username
    assert result[4]["username"] == erin.username


@pytest.mark.django_db
def test_team_members_remove__when_removing_member__succeeds(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    just_a_member = TeamMemberFactory(team=team, role="member")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/remove/",
        json.dumps({"username": just_a_member.user.username}),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["team_name"] == team.name
    assert response_json["username"] == just_a_member.user.username


@pytest.mark.django_db
def test_team_members_remove__when_removing_member__fails_because_user_is_not_a_member_in_team(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)
    another_team = TeamFactory()
    member_in_another_team = TeamMemberFactory(team=another_team, role="owner")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/remove/",
        json.dumps({"username": member_in_another_team.user.username}),
        content_type="application/json",
    )

    assert response.status_code == 404
    response_json = response.json()
    assert response_json["detail"] == "Not found."


@pytest.mark.django_db
def test_team_members_remove__when_removing_member__fails_because_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/cyberstorm/team/GhostTeam/members/remove/",
        json.dumps({"username": user.username}),
        content_type="application/json",
    )

    assert response.status_code == 404
    response_json = response.json()
    assert response_json["detail"] == "Not found."


@pytest.mark.django_db
def test_team_members_remove__when_removing_member__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    just_a_member = TeamMemberFactory(team=team, role="member")

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/members/remove/",
        json.dumps({"username": just_a_member.user.username}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert TeamMember.objects.filter(team=team, user=user).count() == 1


@pytest.mark.django_db
def test_team_service_account_list_api_view__for_member__returns_only_service_accounts(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    TeamMemberFactory(team=team, user=user, role="member")
    sa = ServiceAccountFactory(owner=team)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/service-account/")
    result = response.json()

    assert len(result) == 1
    assert result[0]["identifier"] == str(sa.uuid)
    assert result[0]["name"] == sa.user.first_name
    assert result[0]["last_used"] is None


@pytest.mark.django_db
def test_team_service_account_list_api_view__for_member__sorts_results(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    bob = User.objects.create(username="Bob", first_name="Bob")
    charlie = User.objects.create(username="Charlie", first_name="Charlie")
    alice = User.objects.create(username="Alice", first_name="Alice")
    ServiceAccountFactory(owner=team, user=bob)
    ServiceAccountFactory(owner=team, user=charlie)
    ServiceAccountFactory(owner=team, user=alice)
    TeamMemberFactory(team=team, user=user, role="member")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/cyberstorm/team/{team.name}/service-account/")
    result = response.json()

    assert len(result) == 3
    assert result[0]["name"] == alice.first_name
    assert result[1]["name"] == bob.first_name
    assert result[2]["name"] == charlie.first_name


@pytest.mark.django_db
def test_team_member_add_api_view__when_adding_a_member__succeeds(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    team_member = TeamMemberFactory(team=team, role="owner")
    api_client.force_authenticate(team_member.user)

    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/member/add/",
        json.dumps({"username": user.username, "role": "owner"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["username"] == user.username
    assert response_json["role"] == "owner"
    assert response_json["team"] == team.name


@pytest.mark.django_db
def test_team_member_add_api_view__when_adding_a_member__fails_because_team_doesnt_exist(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    team_member = TeamMemberFactory(team=team, role="owner")
    api_client.force_authenticate(team_member.user)

    response = api_client.post(
        "/api/cyberstorm/team/FakeTeam/member/add/",
        json.dumps({"username": user.username, "role": "owner"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found."


@pytest.mark.django_db
def test_team_member_add_api_view__when_adding_a_member__fails_because_user_is_already_in_team(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    team_member = TeamMemberFactory(team=team, role="owner")
    api_client.force_authenticate(team_member.user)

    response1 = api_client.post(
        f"/api/cyberstorm/team/{team.name}/member/add/",
        json.dumps({"username": user.username, "role": "owner"}),
        content_type="application/json",
    )

    assert response1.status_code == 200

    response2 = api_client.post(
        f"/api/cyberstorm/team/{team.name}/member/add/",
        json.dumps({"username": user.username, "role": "owner"}),
        content_type="application/json",
    )

    assert response2.status_code == 400
    assert (
        "Team Member with this User and Team already exists."
        in response2.json()["__all__"]
    )


@pytest.mark.django_db
def test_team_member_add_api_view__when_adding_a_member__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    team: Team,
    user: UserType,
):
    response = api_client.post(
        f"/api/cyberstorm/team/{team.name}/member/add/",
        json.dumps({"username": user.username, "role": "owner"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert (
        Team.objects.get(pk=team.pk)
        .members.filter(user__username=user.username)
        .count()
        == 0
    )


@pytest.mark.django_db
def test_team_create__when_creating_a_team__succeeds(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/cyberstorm/teams/create/",
        json.dumps({"name": "CoolestTeamNameEver"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["name"] == "CoolestTeamNameEver"
    assert (
        Team.objects.get(name="CoolestTeamNameEver")
        .members.filter(user__username=user.username)
        .count()
        == 1
    )


@pytest.mark.django_db
def test_team_create__when_creating_a_team__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    user: UserType,
):
    response = api_client.post(
        "/api/cyberstorm/teams/create/",
        json.dumps({"name": "CoolestTeamNameEver"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert Team.objects.filter(name="CoolestTeamNameEver").count() == 0


@pytest.mark.django_db
def test_team_create__when_creating_a_team__fails_because_team_with_provided_name_exists(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/cyberstorm/teams/create/",
        json.dumps({"name": team.name}),
        content_type="application/json",
    )

    assert response.status_code == 400
    response_json = response.json()
    assert "A team with the provided name already exists" in response_json["name"]
