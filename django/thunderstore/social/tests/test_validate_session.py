from typing import Any, Dict, Optional

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import override_settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.core.types import UserType


@pytest.mark.django_db
def test_missing_session_key_causes_401_response(api_client: APIClient) -> None:
    response = _get(api_client)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."


@pytest.mark.django_db
def test_invalid_session_key_causes_401_response(api_client: APIClient) -> None:
    response = _get(api_client, "potato")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."


@pytest.mark.django_db
@override_settings(SESSION_COOKIE_AGE=0)
def test_expired_session_key_causes_401_response(
    api_client: APIClient, user: UserType
) -> None:
    session_key = _create_session(user)

    response = _get(api_client, session_key)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."


@pytest.mark.django_db
def test_valid_session_key_causes_200_response(
    api_client: APIClient, user: UserType
) -> None:
    session_key = _create_session(user)

    response = _get(api_client, session_key)

    assert response.status_code == 200
    assert response.json()["detail"] == "OK"


def _create_session(user: UserType) -> str:
    store = SessionStore()
    store.create()
    store["_auth_user_id"] = user.pk
    store.save()
    return store.session_key


def _get(client: APIClient, session_key: Optional[str] = None) -> Response:
    url = reverse("api:experimental:auth.validate")
    kwargs: Dict[str, Any] = {"content_type": "application/json"}

    if session_key:
        kwargs["HTTP_AUTHORIZATION"] = f"Session {session_key}"

    return client.get(url, **kwargs)
