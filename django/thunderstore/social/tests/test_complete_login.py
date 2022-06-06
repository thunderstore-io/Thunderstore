import json
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils.text import slugify
from rest_framework.response import Response
from rest_framework.test import APIClient
from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.social.api.experimental.views.complete_login import (
    get_or_create_auth_user,
    get_unique_username,
)
from thunderstore.social.permissions import OauthSharedSecretPermission
from thunderstore.social.providers import (
    DiscordOauthHelper,
    GitHubOauthHelper,
    UserInfoSchema,
)

User = get_user_model()


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
        "extra_data": {"foo": "bar"},
        "name": "Foo Bar",
        "provider": "github",
        "uid": "1234",
        "username": "Foo",
    }
)
USER_INFO = {
    "email": "x@example.org",
    "extra_data": {"x": "y"},
    "name": "X Y",
    "provider": "github",
    "uid": "uid",
    "username": "x",
}


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
    assert not Session.objects.exists()
    url = _get_url(provider)

    response = _post(api_client, url)
    data = response.json()

    assert (response.status_code) == 200
    assert Session.objects.filter(pk=data["session_id"]).exists()
    assert data["email"] == RETURN_VALUE.email
    assert data["username"] == slugify(RETURN_VALUE.username)


def test_get_unique_username_rejects_empty_usernames() -> None:
    with pytest.raises(ValueError, match="Username may not be empty"):
        get_unique_username("")


@pytest.mark.django_db
def test_get_unique_username_clips_usernames_only_when_needed() -> None:
    max_length = User._meta.get_field("username").max_length
    max_str = "x" * max_length

    assert get_unique_username(max_str) == max_str
    assert get_unique_username(f"{max_str}!") == max_str


@pytest.mark.django_db
def test_get_unique_username_adds_random_suffixes_only_when_needed() -> None:
    username1 = get_unique_username("Fabio")
    User.objects.create(username=username1)
    username2 = get_unique_username("Fabio")
    User.objects.create(username=username2)
    username3 = get_unique_username(username2)

    assert username2 != username1
    assert username3 != username1
    assert username3 != username2


@pytest.mark.django_db
def test_get_or_create_auth_user_creates_user_without_password() -> None:
    ui = UserInfoSchema.parse_obj(USER_INFO)

    user = get_or_create_auth_user(ui)

    assert not user.has_usable_password()


@pytest.mark.django_db
def test_get_or_create_auth_user_creates_user_only_when_needed() -> None:
    assert User.objects.count() == 0
    assert UserSocialAuth.objects.count() == 0

    # Create original user.
    ui = UserInfoSchema.parse_obj(USER_INFO)
    user1 = get_or_create_auth_user(ui)
    assert User.objects.count() == 1
    assert UserSocialAuth.objects.count() == 1
    assert UserSocialAuth.objects.latest("modified").user_id == user1.pk

    # Using the same information should return the original user.
    user2 = get_or_create_auth_user(ui)
    assert User.objects.count() == 1
    assert UserSocialAuth.objects.count() == 1
    assert user2.pk == user1.pk
    assert UserSocialAuth.objects.latest("modified").user_id == user2.pk

    # We can't know if user "x" in GitHub is the same person as user "x"
    # in Discord, so we need to create another user.
    ui.provider = "discord"
    user3 = get_or_create_auth_user(ui)
    assert User.objects.count() == 2
    assert UserSocialAuth.objects.count() == 2
    assert user3.pk != user1.pk
    assert UserSocialAuth.objects.latest("modified").user_id == user3.pk


@pytest.mark.django_db
def test_get_or_create_auth_user_updates_extra_data() -> None:
    assert UserSocialAuth.objects.count() == 0

    ui = UserInfoSchema.parse_obj(USER_INFO)
    get_or_create_auth_user(ui)
    assert UserSocialAuth.objects.count() == 1
    usa1 = UserSocialAuth.objects.get()
    assert usa1.extra_data["x"] == "y"

    ui.extra_data = {"x": "z"}
    get_or_create_auth_user(ui)
    assert UserSocialAuth.objects.count() == 1
    usa2 = UserSocialAuth.objects.get()
    assert usa2.extra_data["x"] == "z"
    assert usa2.modified > usa1.modified


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
