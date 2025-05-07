import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import NamespaceFactory
from thunderstore.repository.models.team import Team


def get_create_team_url() -> str:
    return "/api/cyberstorm/team/create/"


def make_request(api_client: APIClient, team_name: str):
    response = api_client.post(
        path=get_create_team_url(),
        data=json.dumps({"name": team_name}),
        content_type="application/json",
    )
    return response


@pytest.mark.django_db
def test_create_team_success(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)

    team_count = Team.objects.filter(name="CoolestTeamNameEver").count()
    assert team_count == 0

    response = make_request(api_client, "CoolestTeamNameEver")
    assert response.status_code == 201
    assert response.json()["name"] == "CoolestTeamNameEver"

    team_count = Team.objects.filter(name="CoolestTeamNameEver").count()
    assert team_count == 1


@pytest.mark.django_db
def test_create_team_fail_because_user_is_not_authenticated(api_client: APIClient):
    response = make_request(api_client, "CoolestTeamNameEver")
    assert Team.objects.filter(name="CoolestTeamNameEver").count() == 0
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."
    assert Team.objects.filter(name="CoolestTeamNameEver").count() == 0


@pytest.mark.django_db
def test_create_team__fail_because_team_with_provided_name_exists(
    api_client: APIClient,
    user: UserType,
    team: Team,
):
    api_client.force_authenticate(user)
    response = make_request(api_client, team.name)
    expected_response = {
        "non_field_errors": ["A team with the provided name already exists"]
    }

    assert response.status_code == 400
    assert response.json() == expected_response


@pytest.mark.django_db
def test_create_team__fail_because_team_with_provided_namespace_exists(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)
    NamespaceFactory(name="CoolestTeamNameEver")
    response = make_request(api_client, "CoolestTeamNameEver")
    expected_response = {
        "non_field_errors": ["A namespace with the provided name already exists"]
    }

    assert response.status_code == 400
    assert response.json() == expected_response


@pytest.mark.django_db
def test_create_team_with_too_long_name(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)
    response = make_request(api_client, "a" * 65)

    assert response.status_code == 400
    error_message = "Ensure this field has no more than 64 characters."
    assert error_message in response.json()["name"]


@pytest.mark.django_db
def test_create_team_with_invalid_team_name(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)
    response = make_request(api_client, "hello_")

    assert response.status_code == 400
    error_message = (
        "Author name can only contain a-z A-Z 0-9 _ "
        "characters and must not start or end with _"
    )
    assert error_message in response.json()["name"]


@pytest.mark.django_db
def test_create_team_with_blank_name(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)
    response = make_request(api_client, "")

    assert response.status_code == 400
    error_message = "This field may not be blank."
    assert error_message in response.json()["name"]


@pytest.mark.django_db
def test_create_team_without_name(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)
    response = make_request(api_client, None)

    assert response.status_code == 400
    error_message = "This field may not be null."
    assert error_message in response.json()["name"]


@pytest.mark.django_db
def test_create_team_without_data(api_client: APIClient, user: UserType):
    api_client.force_authenticate(user)
    response = api_client.post(
        path=get_create_team_url(),
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400
    error_message = "This field is required."
    assert error_message in response.json()["name"]


@pytest.mark.django_db
def test_create_team_with_service_account(api_client: APIClient, service_account):
    api_client.force_authenticate(service_account.user)
    assert Team.objects.filter(name="CoolestTeamNameEver").count() == 0
    response = make_request(api_client, "CoolestTeamNameEver")
    expected_response = {"non_field_errors": ["Service accounts cannot create teams"]}

    assert response.status_code == 403
    assert response.json() == expected_response
    assert Team.objects.filter(name="CoolestTeamNameEver").count() == 0
