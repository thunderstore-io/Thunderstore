import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType

User = get_user_model()


def get_delete_user_url(username: str) -> str:
    return f"/api/cyberstorm/user/{username}/delete/"


def get_disconnect_user_linked_account_url(username: str, provider: str) -> str:
    return f"/api/cyberstorm/user/{username}/linked-accounts/{provider}/disconnect/"


@pytest.mark.django_db
def test_delete_user_success(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)

    assert User.objects.filter(username=user.username).exists()
    url = get_delete_user_url(user.username)
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 204
    assert not User.objects.filter(username=user.username).exists()


@pytest.mark.django_db
def test_delete_user_fail_unauthenticated(api_client: APIClient, user: UserType):
    url = get_delete_user_url(user.username)
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_delete_user_not_found(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)
    url = get_delete_user_url("not_found")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_user_fail_permission_denied(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)
    another_user = UserFactory()
    url = get_delete_user_url(another_user.username)
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_disconnect_user_linked_account_success(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    assert user_with_social_auths.social_auth.filter(provider="discord").exists()
    url = get_disconnect_user_linked_account_url(
        user_with_social_auths.username, "discord"
    )
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 204
    assert not user_with_social_auths.social_auth.filter(provider="discord").exists()


@pytest.mark.django_db
def test_disconnect_user_linked_account_fail_unauthenticated(
    user_with_social_auths: UserType, api_client: APIClient
):
    url = get_disconnect_user_linked_account_url(
        user_with_social_auths.username, "discord"
    )
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_disconnect_user_non_existent_linked_account(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    url = get_disconnect_user_linked_account_url(
        user_with_social_auths.username, "non-existent"
    )
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 404
    assert response.data["detail"] == "Not found."


@pytest.mark.django_db
def test_disconnect_user_with_no_social_auth(user: UserType, api_client: APIClient):
    api_client.force_authenticate(user=user)
    url = get_disconnect_user_linked_account_url(user.username, "non-existent")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 404
    assert response.data["detail"] == "Not found."


@pytest.mark.django_db
def test_disconnect_user_linked_account_fail_permission_denied(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    another_user = UserFactory()
    url = get_disconnect_user_linked_account_url(another_user.username, "discord")
    response = api_client.delete(url, content_type="application/json")
    assert response.status_code == 403
    assert response.data["detail"] == "Cannot disconnect another user's account."


@pytest.mark.django_db
def test_disconnect_user_linked_account_fail_last_linked_account(
    user_with_social_auths: UserType, api_client: APIClient
):
    api_client.force_authenticate(user=user_with_social_auths)
    user_with_social_auths.social_auth.filter(provider="discord").delete()
    url = get_disconnect_user_linked_account_url(
        user_with_social_auths.username, "github"
    )
    response = api_client.delete(url, content_type="application/json")
    expected_response = {"detail": "Cannot disconnect last linked auth method."}
    assert response.status_code == 403
    assert response.json() == expected_response
