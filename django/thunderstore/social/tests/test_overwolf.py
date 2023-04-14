import json
from typing import Optional
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

SECRET = "no_more_secrets"
LOGIN_URL = reverse("api:experimental:auth.overwolf")


def do_login_request(client: APIClient, jwt: Optional[str]) -> Response:
    payload = json.dumps({"jwt": jwt})

    return client.post(
        LOGIN_URL,
        payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
    )


@override_settings(OVERWOLF_CLIENT_ID="")
def test_querying_ow_api__with_undefined_ow_id__raises_exception() -> None:
    with pytest.raises(ImproperlyConfigured):
        overwolf.query_overwolf_jwt_api("path", "jwt")


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_login_request__without_authorization_header__is_rejected(
    api_client: APIClient,
) -> None:
    """
    Test that the endpoint requires the header - further testing auth
    header would just duplicate the tests in test_complete_login.py.
    """
    response = api_client.post(LOGIN_URL, {}, content_type="application/json")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect authentication credentials."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
def test_login_request__without_jwt__is_rejected(api_client: APIClient) -> None:
    response = do_login_request(api_client, jwt="")
    errors = response.json()

    assert response.status_code == 400
    assert len(errors) == 1
    assert len(errors["jwt"]) == 1
    assert errors["jwt"][0] == "This field may not be blank."

    response = do_login_request(api_client, jwt=None)
    errors = response.json()

    assert response.status_code == 400
    assert len(errors) == 1
    assert len(errors["jwt"]) == 1
    assert errors["jwt"][0] == "This field may not be null."


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@patch.object(overwolf, "query_overwolf_jwt_api", return_value=Mock(status_code=401))
def test_login_request__with_invalid_jwt__is_verified_and_rejected(
    mocked_query_api_func, api_client: APIClient
) -> None:
    response = do_login_request(api_client, jwt="invalid")

    assert response.status_code == 401
    mocked_query_api_func.assert_called_once_with("verify", "invalid")


@pytest.mark.django_db
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@patch.object(overwolf, "verify_overwolf_jwt")
@patch.object(
    overwolf,
    "get_overwolf_user_profile",
    return_value=overwolf.OverwolfProfileSchema.parse_obj(
        {"username": "kingsley", "nickname": "Cosmo", "avatar": ""}
    ),
)
def test_login_request__with_valid_information__succeeds(
    mocked_get_profile, mocked_verify, api_client: APIClient
) -> None:
    response = do_login_request(api_client, jwt="mock_jwt")
    data = response.json()

    assert response.status_code == 200
    assert data["username"] == "kingsley"
    assert type(data["session_id"]) == str
    assert data["session_id"] != ""
    mocked_verify.assert_called_once_with("mock_jwt")
    mocked_get_profile.assert_called_once_with("mock_jwt")
