import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.core.types import UserType

User = get_user_model()


def get_delete_user_url() -> str:
    return f"/api/cyberstorm/user/delete/"


def get_disconnect_user_linked_account_url(provider: str) -> str:
    return f"/api/cyberstorm/user/linked-account/{provider}/disconnect/"


@pytest.mark.django_db
def test_delete_user_success(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)

    assert User.objects.filter(username=user.username).exists()
    url = get_delete_user_url()
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 204
    assert not User.objects.filter(username=user.username).exists()


@pytest.mark.django_db
def test_delete_user_fail_unauthenticated(api_client: APIClient, user: UserType):
    url = get_delete_user_url()
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_disconnect_user_linked_account_success(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    assert user_with_social_auths.social_auth.filter(provider="discord").exists()

    url = get_disconnect_user_linked_account_url("discord")
    response = api_client.delete(url, content_type="application/json")

    assert response.status_code == 204
    assert not user_with_social_auths.social_auth.filter(provider="discord").exists()


@pytest.mark.django_db
def test_disconnect_user_linked_account_fail_unauthenticated(api_client: APIClient):
    url = get_disconnect_user_linked_account_url("discord")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_disconnect_user_non_existent_linked_account(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    url = get_disconnect_user_linked_account_url("non-existent")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_disconnect_user_with_no_social_auth(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)
    url = get_disconnect_user_linked_account_url("non-existent")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_disconnect_user_linked_account_fail_last_linked_account(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    user_with_social_auths.social_auth.filter(provider="discord").delete()
    url = get_disconnect_user_linked_account_url("github")

    response = api_client.delete(url, content_type="application/json")
    expected_response = {
        "non_field_errors": ["Cannot disconnect last linked auth method"]
    }

    assert response.status_code == 403
    assert response.json() == expected_response
