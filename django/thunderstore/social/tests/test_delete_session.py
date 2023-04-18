import pytest
from django.contrib.sessions.models import Session
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.core.types import UserType

URL = reverse("api:experimental:auth.delete")


@pytest.mark.django_db
def test_delete_request__without_auth_header__is_rejected(
    api_client: APIClient,
    user: UserType,
) -> None:
    assert Session.objects.count() == 0

    api_client.force_login(user)

    assert Session.objects.count() == 1

    response = api_client.post(URL, content_type="application/json")

    assert response.status_code == 401
    assert Session.objects.count() == 1


@pytest.mark.django_db
def test_delete_request__with_nonexisting_sessionid__is_rejected(
    api_client: APIClient,
    user: UserType,
) -> None:
    assert Session.objects.count() == 0

    api_client.force_login(user)

    assert Session.objects.count() == 1

    response = api_client.post(
        URL,
        content_type="application/json",
        HTTP_AUTHORIZATION="Session let-me-in",
    )

    assert response.status_code == 401
    assert Session.objects.count() == 1


@pytest.mark.django_db
def test_logout_request__with_existing_sessionid__succeeds(
    api_client: APIClient,
    user: UserType,
) -> None:
    assert Session.objects.count() == 0

    api_client.force_login(user)

    assert Session.objects.count() == 1

    session_key = api_client.cookies["sessionid"].value
    response = api_client.post(
        URL,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Session {session_key}",
    )

    assert response.status_code == 204
    assert Session.objects.count() == 0
