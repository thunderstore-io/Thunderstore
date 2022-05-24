import json
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.social.permissions import OauthSharedSecretPermission
from thunderstore.social.providers import (
    DiscordOauthHelper,
    GitHubOauthHelper,
    UserInfoSchema,
)

SECRET = "ABC123"
PAYLOAD = json.dumps(
    {
        "code": "code",
        "redirect_uri": "redirect_uri",
    }
)
RETURN_VALUE = UserInfoSchema.parse_obj(
    {
        "email": "foo@bar.com",
        "name": "Foo Bar",
        "uid": "1234",
        "username": "Foo",
    }
)


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", "")
@pytest.mark.django_db
def test_unconfigured_shared_secret_is_caught(api_client: APIClient) -> None:
    response = _post(api_client)

    assert response.status_code == 500
    assert response.json()["detail"] == "Server is improperly configured"


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_missing_authorization_header_is_caught(api_client: APIClient) -> None:
    url = _get_url()

    response = api_client.post(url, PAYLOAD, content_type="application/json")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect authentication credentials."


@patch.multiple(
    GitHubOauthHelper,
    complete_login=Mock(),
    get_user_info=Mock(return_value=RETURN_VALUE),
)
@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "header, expected_response_code",
    (
        ("", 401),
        ("TS-Secret", 401),
        ("TS-Secret ", 401),
        ("TS-Secret not-a-secret", 401),
        (f"Bearer {SECRET}", 401),
        (f"Token {SECRET}", 401),
        (f"TS-Secret {SECRET}", 200),
    ),
)
def test_invalid_authorization_header_is_caught(
    api_client: APIClient, header: Optional[str], expected_response_code: int
) -> None:
    url = _get_url()

    response = api_client.post(
        url,
        PAYLOAD,
        content_type="application/json",
        HTTP_AUTHORIZATION=header,
    )

    assert response.status_code == expected_response_code


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, redirect_uri",
    (
        (False, False),
        (True, False),
        (False, True),
    ),
)
def test_parameters_are_provided(
    api_client: APIClient,
    code: bool,
    redirect_uri: bool,
) -> None:
    data = {}

    if code:
        data["code"] = "code"
    if redirect_uri:
        data["redirect_uri"] = "uri"

    payload = json.dumps(data)

    response = _post(api_client, payload=payload)
    errors = response.json()

    assert (response.status_code) == 400

    for field, value in (
        ("code", code),
        ("redirect_uri", redirect_uri),
    ):
        if value:
            assert field not in errors
        else:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field is required."


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, redirect_uri",
    (
        ("", ""),
        (None, None),
        ("code", ""),
        ("code", None),
        ("", "uri"),
        (None, "uri"),
    ),
)
def test_parameters_are_not_emptyish(
    api_client: APIClient,
    code: Optional[str],
    redirect_uri: Optional[str],
) -> None:
    payload = json.dumps(
        {
            "code": code,
            "redirect_uri": redirect_uri,
        }
    )

    response = _post(api_client, payload=payload)
    errors = response.json()

    assert (response.status_code) == 400

    for field, value in (
        ("code", code),
        ("redirect_uri", redirect_uri),
    ):
        if value:
            assert field not in errors
        elif value is None:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field may not be null."
        else:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field may not be blank."


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_unknown_providers_are_rejected(api_client: APIClient) -> None:
    url = _get_url("acme")

    response = _post(api_client, url)

    assert (response.status_code) == 400
    assert (response.json()) == "Unsupported OAuth provider"


@patch.object(OauthSharedSecretPermission, "SHARED_SECRET", SECRET)
@patch.multiple(
    GitHubOauthHelper,
    complete_login=Mock(),
    get_user_info=Mock(return_value=RETURN_VALUE),
)
@patch.multiple(
    DiscordOauthHelper,
    complete_login=Mock(),
    get_user_info=Mock(return_value=RETURN_VALUE),
)
@pytest.mark.django_db
@pytest.mark.parametrize("provider", ("github", "discord"))
def test_valid_request(api_client: APIClient, provider: str) -> None:
    url = _get_url(provider)

    response = _post(api_client, url)

    assert (response.status_code) == 200
    assert (response.json()["session_id"]) == "TODO"


def _get_url(provider: str = "github") -> str:
    return reverse("api:experimental:auth.complete", kwargs={"provider": provider})


def _post(
    client: APIClient, url: Optional[str] = None, payload: Any = None
) -> Response:
    return client.post(
        url or _get_url(),
        payload or PAYLOAD,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
    )
