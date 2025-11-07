import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.repository.models.team import Team, TeamMember

User = get_user_model()


def get_create_service_account_url(team_name: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/service-account/create/"


def get_delete_service_account_url(uuid: str) -> str:
    return f"/api/cyberstorm/service-account/{uuid}/delete/"


@pytest.mark.django_db
def test_create_service_account_success(api_client: APIClient, team_owner: TeamMember):
    api_client.force_authenticate(team_owner.user)

    url = get_create_service_account_url(team_owner.team.name)
    data = json.dumps({"nickname": "CoolestTeamServiceAccountName"})

    response = api_client.post(url, data, content_type="application/json")

    expected_response = {
        "nickname": "CoolestTeamServiceAccountName",
        "team_name": team_owner.team.name,
        "api_token": "tss_",
    }

    service_account_count = ServiceAccount.objects.filter(
        owner__name=team_owner.team.name,
        user__first_name="CoolestTeamServiceAccountName",
    ).count()

    assert response.status_code == 201
    assert response.json()["nickname"] == expected_response["nickname"]
    assert response.json()["team_name"] == expected_response["team_name"]
    assert response.json()["api_token"][:4] == expected_response["api_token"]
    assert service_account_count == 1


@pytest.mark.django_db
def test_create_service_account_not_authenticated(
    api_client: APIClient, team_owner: TeamMember
):
    url = get_create_service_account_url(team_owner.team.name)
    data = json.dumps({"nickname": "CoolestTeamServiceAccountName"})

    response = api_client.post(url, data, content_type="application/json")
    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == 401
    assert response.json() == expected_response


@pytest.mark.django_db
def test_create_service_account_fails_because_nickname_too_long(
    api_client: APIClient,
    team_owner: TeamMember,
):
    api_client.force_authenticate(team_owner.user)
    url = get_create_service_account_url(team_owner.team.name)
    data = json.dumps({"nickname": "LongestCoolestTeamServiceAccountNameEver"})

    response = api_client.post(url, data, content_type="application/json")

    expected_response = {
        "nickname": ["Ensure this field has no more than 32 characters."]
    }

    service_account_count = ServiceAccount.objects.filter(
        owner__name=team_owner.team.name,
        user__first_name="LongestCoolestTeamServiceAccountNameEver",
    ).count()

    assert response.status_code == 400
    assert response.json() == expected_response
    assert service_account_count == 0


@pytest.mark.django_db
def test_create_service_account_fail_because_user_is_not_team_member(
    api_client: APIClient,
    team: Team,
):
    non_team_user = User.objects.create()
    api_client.force_authenticate(non_team_user)

    url = get_create_service_account_url(team.name)
    data = json.dumps({"nickname": "CoolestTeamServiceAccountName"})

    response = api_client.post(url, data, content_type="application/json")
    account_count = ServiceAccount.objects.filter(
        owner__name=team.name, user__first_name="CoolestTeamServiceAccountName"
    ).count()

    expected_response = {"non_field_errors": ["Must be a member to access team"]}

    assert response.status_code == 403
    assert account_count == 0
    assert response.json() == expected_response


@pytest.mark.django_db
def test_create_service_account_fail_because_user_is_not_team_owner(
    api_client: APIClient,
    team: Team,
    team_member: TeamMember,
):
    api_client.force_authenticate(team_member.user)
    url = get_create_service_account_url(team.name)
    data = json.dumps({"nickname": "CoolestTeamServiceAccountName"})

    response = api_client.post(url, data, content_type="application/json")
    account_count = ServiceAccount.objects.filter(
        owner__name=team.name, user__first_name="CoolestTeamServiceAccountName"
    ).count()

    expected_response = {
        "non_field_errors": ["Must be an owner to create a service account"]
    }

    assert response.status_code == 403
    assert account_count == 0
    assert response.json() == expected_response


@pytest.mark.django_db
def test_delete_service_account_success(
    api_client: APIClient,
    team_owner: TeamMember,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    api_client.force_authenticate(team_owner.user)
    url = get_delete_service_account_url(service_account.uuid)
    response = api_client.delete(path=url, content_type="application/json")

    assert response.status_code == 204
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 0


@pytest.mark.django_db
def test_delete_service_account_fail_user_is_not_authenticated(
    api_client: APIClient,
    team: Team,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    url = get_delete_service_account_url(service_account.uuid)
    response = api_client.delete(path=url, content_type="application/json")
    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == 401
    assert response.json() == expected_response
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1


@pytest.mark.django_db
def test_delete_service_account_fails_because_user_is_not_team_member(
    api_client: APIClient,
    team: Team,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    non_team_user = User.objects.create()
    api_client.force_authenticate(non_team_user)

    url = get_delete_service_account_url(service_account.uuid)
    response = api_client.delete(path=url, content_type="application/json")
    expected_response = {"non_field_errors": ["Must be a member to access team"]}

    assert response.status_code == 403
    assert response.json() == expected_response
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1


@pytest.mark.django_db
def test_delete_service_account_fail_because_user_is_not_team_owner(
    api_client: APIClient,
    team_member: TeamMember,
    team: Team,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    api_client.force_authenticate(team_member.user)
    url = get_delete_service_account_url(service_account.uuid)
    response = api_client.delete(path=url, content_type="application/json")
    expected_response = {
        "non_field_errors": ["Must be an owner to delete a service account"]
    }

    assert response.status_code == 403
    assert response.json() == expected_response
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1
