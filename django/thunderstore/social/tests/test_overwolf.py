import json
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.social.api.experimental.views import overwolf
from thunderstore.social.permissions import (
    ImproperlyConfigured,
    OauthSharedSecretPermission,
)

PROFILE = {"username": "kingsley", "nickname": "Cosmo", "avatar": ""}
SECRET = "no_more_secrets"
URL = reverse("api:experimental:auth.overwolf")


@override_settings(OVERWOLF_CLIENT_ID="")
def test_unconfigured_overwolf_id_is_caught() -> None:
    with pytest.raises(ImproperlyConfigured):
        overwolf.query_overwolf_jwt_api("path", "jwt")


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_missing_authorization_header_is_caught(api_client: APIClient) -> None:
    """
    Test that the endpoint requires the header - further testing auth
    header would just duplicate the tests in test_complete_login.py.
    """
    response = api_client.post(URL, {}, content_type="application/json")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect authentication credentials."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_missing_jwt_is_caught(api_client: APIClient) -> None:
    response = _post(api_client)
    errors = response.json()

    assert response.status_code == 400
    assert len(errors) == 1
    assert len(errors["jwt"]) == 1
    assert errors["jwt"][0] == "This field may not be blank."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@patch.object(overwolf, "query_overwolf_jwt_api", return_value=Mock(status_code=401))
def test_jwt_is_verified(mocked_func, api_client: APIClient) -> None:
    jwt = "fake_jwt"
    response = _post(api_client, jwt)

    assert response.status_code == 401
    mocked_func.assert_called_once_with("verify", jwt)


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@patch.object(overwolf, "verify_overwolf_jwt")
@patch.object(
    overwolf,
    "get_overwolf_user_profile",
    return_value=overwolf.OverwolfProfileSchema.parse_obj(PROFILE),
)
def test_request_succeeds(
    mocked_get_profile, mocked_verify, api_client: APIClient
) -> None:
    jwt = "fake_jwt"
    response = _post(api_client, jwt)
    data = response.json()

    assert response.status_code == 200
    assert data["username"] == PROFILE["username"]
    assert type(data["session_id"]) == str
    assert data["session_id"] != ""
    mocked_verify.assert_called_once_with(jwt)
    mocked_get_profile.assert_called_once_with(jwt)


def _post(client: APIClient, jwt: str = "") -> Response:
    payload = json.dumps({"jwt": jwt})

    return client.post(
        URL,
        payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
    )
