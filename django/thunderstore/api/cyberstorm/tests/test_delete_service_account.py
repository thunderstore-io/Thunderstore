import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.repository.models.team import Team, TeamMember

User = get_user_model()


def get_delete_service_account_url(team_name: str) -> str:
    return f"/api/cyberstorm/team/{team_name}/service-account/delete/"


def make_request(api_client: APIClient, team_name: str, account: ServiceAccount):
    return api_client.post(
        path=get_delete_service_account_url(team_name),
        data=json.dumps({"uuid": str(account.uuid)}),
        content_type="application/json",
    )


@pytest.mark.django_db
def test_delete_service_account_success(
    api_client: APIClient,
    team_owner: TeamMember,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    api_client.force_authenticate(team_owner.user)
    response = make_request(api_client, team_owner.team.name, service_account)

    assert response.status_code == 204
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 0


@pytest.mark.django_db
def test_delete_service_account_fail_user_is_not_authenticated(
    api_client: APIClient,
    team: Team,
    service_account: ServiceAccount,
):
    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1

    response = make_request(api_client, team.name, service_account)
    assert response.status_code == 401

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

    response = make_request(api_client, team.name, service_account)
    assert response.status_code == 403

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

    response = make_request(api_client, team.name, service_account)
    assert response.status_code == 403

    assert ServiceAccount.objects.filter(uuid=service_account.uuid).count() == 1
