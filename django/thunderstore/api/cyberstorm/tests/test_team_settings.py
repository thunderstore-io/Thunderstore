import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.repository.models import Team


@pytest.mark.django_db
def test_team_settings_get_succeeds(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    team.donation_link = "https://test.url"
    team.save()
    api_client.force_authenticate(user)

    response = api_client.get(
        f"/api/cyberstorm/team/{team.name}/settings/",
    )

    assert response.status_code == 200
    assert response.json() == {
        "identifier": team.pk,
        "name": team.name,
        "donation_link": "https://test.url",
    }


@pytest.mark.django_db
def test_team_settings_get_succeeds_no_donation_link(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    response = api_client.get(
        f"/api/cyberstorm/team/{team.name}/settings/",
    )

    assert response.status_code == 200
    assert response.json() == {
        "identifier": team.pk,
        "name": team.name,
        "donation_link": None,
    }


@pytest.mark.django_db
def test_team_settings_get_fails_user_not_authenticated(
    api_client: APIClient,
    team: Team,
):
    response = api_client.get(
        f"/api/cyberstorm/team/{team.name}/settings/",
    )

    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == 401
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_get_fails_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    response = api_client.get(
        "/api/cyberstorm/team/FakeTeam/settings/",
    )

    expected_response = {"detail": "Not found."}

    assert response.status_code == 404
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_get_fails_user_not_team_member(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    api_client.force_authenticate(user)

    response = api_client.get(
        f"/api/cyberstorm/team/{team.name}/settings/",
    )

    expected_response = {"non_field_errors": ["Must be a member to access team"]}

    assert response.status_code == 403
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_get_fails_user_not_owner(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="member")
    api_client.force_authenticate(user)

    response = api_client.get(
        f"/api/cyberstorm/team/{team.name}/settings/",
    )

    expected_response = {"non_field_errors": ["Must be an owner to edit team info"]}

    assert response.status_code == 403
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_update_succeeds(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    new_donation_link = "https://test.url"

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["donation_link"] == new_donation_link
    assert Team.objects.get(pk=team.pk).donation_link == new_donation_link


@pytest.mark.django_db
def test_team_settings_update_succeeds_unset_donation_link(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    team.donation_link = "https://test.url"
    team.save()
    api_client.force_authenticate(user)

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": None}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["donation_link"] is None
    assert Team.objects.get(pk=team.pk).donation_link is None


@pytest.mark.django_db
def test_team_settings_update_fails_user_not_authenticated(
    api_client: APIClient,
    team: Team,
):
    new_donation_link = "https://test.url"

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == 401
    assert response.json() == expected_response
    assert Team.objects.get(pk=team.pk).donation_link is None


@pytest.mark.django_db
def test_team_settings_update_fails_validation(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="owner")
    api_client.force_authenticate(user)

    new_bad_donation_link = "http://test.url"

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": new_bad_donation_link}),
        content_type="application/json",
    )

    expected_response = {"donation_link": ["Enter a valid URL."]}

    assert response.status_code == 400
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_update_fails_user_not_owner(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    TeamMemberFactory(team=team, user=user, role="member")
    api_client.force_authenticate(user)

    new_donation_link = "https://test.url"

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    expected_response = {"non_field_errors": ["Must be an owner to edit team info"]}

    assert response.status_code == 403
    assert response.json() == expected_response
    assert Team.objects.get(pk=team.pk).donation_link is None


@pytest.mark.django_db
def test_team_settings_update_fails_team_does_not_exist(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)

    new_donation_link = "https://test.url"

    response = api_client.patch(
        "/api/cyberstorm/team/FakeTeam/settings/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    expected_response = {"detail": "Not found."}

    assert response.status_code == 404
    assert response.json() == expected_response


@pytest.mark.django_db
def test_team_settings_update_fails_user_not_team_member(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    api_client.force_authenticate(user)

    new_donation_link = "https://test.url"

    response = api_client.patch(
        f"/api/cyberstorm/team/{team.name}/settings/",
        json.dumps({"donation_link": new_donation_link}),
        content_type="application/json",
    )

    expected_response = {"non_field_errors": ["Must be a member to access team"]}

    assert response.status_code == 403
    assert response.json() == expected_response
