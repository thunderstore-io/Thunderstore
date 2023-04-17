import json
from typing import Optional
from unittest.mock import patch

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.social.permissions import OauthSharedSecretPermission

SECRET = "no_more_secrets"
LOGOUT_URL = reverse("api:experimental:auth.delete")


def do_logout_request(client: APIClient, sessionid: Optional[str]) -> Response:
    payload = json.dumps({"sessionid": sessionid})

    return client.post(
        LOGOUT_URL,
        payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
    )


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_logout_request__without_authorization_header__is_rejected(
    api_client: APIClient,
) -> None:
    """
    Test that the endpoint requires the header - further testing auth
    header would just duplicate the tests in test_complete_login.py.
    """
    response = api_client.post(LOGOUT_URL, {}, content_type="application/json")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect authentication credentials."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_logout_request__without_sessionid__is_rejected(api_client: APIClient) -> None:
    response = do_logout_request(api_client, sessionid="")
    errors = response.json()

    assert response.status_code == 400
    assert len(errors) == 1
    assert len(errors["sessionid"]) == 1
    assert errors["sessionid"][0] == "This field may not be blank."

    response = do_logout_request(api_client, sessionid=None)
    errors = response.json()

    assert response.status_code == 400
    assert len(errors) == 1
    assert len(errors["sessionid"]) == 1
    assert errors["sessionid"][0] == "This field may not be null."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_logout_request__with_nonexisting_sessionid__succeeds(
    api_client: APIClient,
) -> None:
    response = do_logout_request(api_client, sessionid="no_such_session")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_logout_request__with_existing_sessionid__succeeds(
    api_client: APIClient,
) -> None:
    # Start with no sessions.
    assert not Session.objects.exists()

    # Create session.
    session = SessionStore(None)
    session.create()

    assert Session.objects.count() == 1

    # Logout the session.
    response = do_logout_request(api_client, sessionid=session.session_key)

    assert response.status_code == 204
    assert response.content == b""
    assert not Session.objects.exists()
