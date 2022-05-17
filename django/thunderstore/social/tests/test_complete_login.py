import json
from typing import Optional
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

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
        "secret": SECRET,
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


@override_settings(OAUTH_SHARED_SECRET="")
@pytest.mark.django_db
def test_unconfigured_shared_secret_is_caught(api_client: APIClient) -> None:
    url = _get_url()

    response = api_client.post(url, PAYLOAD, content_type="application/json")

    assert (response.status_code) == 500
    assert (response.json()) == "Improperly configured"


@override_settings(OAUTH_SHARED_SECRET=SECRET)
@pytest.mark.django_db
def test_shared_secret_is_provided(api_client: APIClient) -> None:
    url = _get_url()
    payload = json.dumps(
        {
            "code": "code",
            "redirect_uri": "redirect_uri",
            "secret": "Ken sent me",
        }
    )

    response = api_client.post(url, payload, content_type="application/json")

    assert (response.status_code) == 400
    assert (response.json()) == "Invalid secret"


@override_settings(OAUTH_SHARED_SECRET=SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, redirect_uri, secret",
    (
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, False, True),
        (False, True, False),
        (False, True, True),
        (False, False, True),
    ),
)
def test_parameters_are_provided(
    api_client: APIClient,
    code: bool,
    redirect_uri: bool,
    secret: bool,
) -> None:
    url = _get_url()
    data = {}

    if code:
        data["code"] = "code"
    if redirect_uri:
        data["redirect_uri"] = "uri"
    if secret:
        data["secret"] = "secret"

    payload = json.dumps(data)

    response = api_client.post(url, payload, content_type="application/json")
    errors = response.json()

    assert (response.status_code) == 400

    for field, value in (
        ("code", code),
        ("redirect_uri", redirect_uri),
        ("secret", secret),
    ):
        if value:
            assert field not in errors
        else:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field is required."


@override_settings(OAUTH_SHARED_SECRET=SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, redirect_uri, secret",
    (
        ("", "", ""),
        (None, None, None),
        ("code", "", ""),
        ("code", None, None),
        ("code", "uri", ""),
        ("code", "uri", None),
        ("code", "", "secret"),
        ("code", None, "secret"),
        ("", "uri", ""),
        (None, "uri", None),
        ("", "uri", "secret"),
        (None, "uri", "secret"),
        ("", "", "uri"),
        (None, None, "secret"),
    ),
)
def test_parameters_are_not_emptyish(
    api_client: APIClient,
    code: Optional[str],
    redirect_uri: Optional[str],
    secret: Optional[str],
) -> None:
    url = _get_url()
    payload = json.dumps(
        {
            "code": code,
            "redirect_uri": redirect_uri,
            "secret": secret,
        }
    )

    response = api_client.post(url, payload, content_type="application/json")
    errors = response.json()

    assert (response.status_code) == 400

    for field, value in (
        ("code", code),
        ("redirect_uri", redirect_uri),
        ("secret", secret),
    ):
        if value:
            assert field not in errors
        elif value is None:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field may not be null."
        else:
            assert len(errors[field]) == 1
            assert errors[field][0] == "This field may not be blank."


@override_settings(OAUTH_SHARED_SECRET=SECRET)
@pytest.mark.django_db
def test_unknown_providers_are_rejected(api_client: APIClient) -> None:
    url = _get_url("acme")

    response = api_client.post(url, PAYLOAD, content_type="application/json")

    assert (response.status_code) == 400
    assert (response.json()) == "Unsupported OAuth provider"


@override_settings(OAUTH_SHARED_SECRET=SECRET)
@pytest.mark.django_db
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
@pytest.mark.parametrize("provider", ("github", "discord"))
def test_valid_request(api_client: APIClient, provider: str) -> None:
    url = _get_url(provider)

    response = api_client.post(url, PAYLOAD, content_type="application/json")

    assert (response.status_code) == 200
    assert (response.json()["session_id"]) == "TODO"


def _get_url(provider: str = "github") -> str:
    return reverse("api:experimental:auth.complete", kwargs={"provider": provider})
