from typing import List, Optional, Type
from unittest.mock import Mock, patch

import pytest
import requests

from thunderstore.social.providers import (
    BaseOauthHelper,
    DiscordOauthHelper,
    GitHubOauthHelper,
    get_helper,
)


@patch.object(
    requests,
    "post",
    return_value=Mock(
        json=lambda: {
            "access_token": "mellon",
            "scope": "read:user,user:email",
            "token_type": "bearer",
        }
    ),
)
def test_complete_login_sets_access_token(mocked_request_post) -> None:
    helper = GitHubOauthHelper("code", "redirect_uri")

    helper.complete_login()

    mocked_request_post.assert_called_once()
    assert helper.token == "mellon"


@pytest.mark.parametrize(
    ("helper_class", "method_name"),
    (
        (DiscordOauthHelper, "get_user_info"),
        (GitHubOauthHelper, "get_user_info"),
        (GitHubOauthHelper, "get_user_email"),
    ),
)
def test_api_methods_check_for_token(
    helper_class: Type[BaseOauthHelper], method_name: str
) -> None:
    helper = helper_class("code", "redirect_uri")

    with pytest.raises(
        Exception,
        match="No token found. Did you call .complete_login()?",
    ):
        api_method = getattr(helper, method_name)
        api_method()


@patch.object(
    requests,
    "get",
    return_value=Mock(
        json=lambda: {
            "email": "foo@bar.com",
            "id": "5678",
            "something": "extra",
            "username": "Foo",
        }
    ),
)
def test_discord_get_user_info(mocked_request_get) -> None:
    helper = DiscordOauthHelper("code", "redirect_uri")
    helper.token = "token"

    info = helper.get_user_info()

    mocked_request_get.assert_called_once()
    assert info.email == "foo@bar.com"
    assert info.extra_data["email"] == "foo@bar.com"
    assert info.extra_data["id"] == "5678"
    assert info.extra_data["something"] == "extra"
    assert info.extra_data["username"] == "Foo"
    assert info.name == ""
    assert info.uid == "5678"
    assert info.username == "Foo"


@patch.object(
    requests,
    "get",
    return_value=Mock(
        json=lambda: {
            "email": "foo@bar.com",
            "id": "5678",
            "login": "Foo",
            "name": "Foo Bar",
            "something": "extra",
        }
    ),
)
def test_github_get_user_info_with_public_email(mocked_request_get) -> None:
    helper = GitHubOauthHelper("code", "redirect_uri")
    helper.token = "token"

    info = helper.get_user_info()

    mocked_request_get.assert_called_once()
    assert info.email == "foo@bar.com"
    assert info.extra_data["email"] == "foo@bar.com"
    assert info.extra_data["id"] == "5678"
    assert info.extra_data["login"] == "Foo"
    assert info.extra_data["name"] == "Foo Bar"
    assert info.extra_data["something"] == "extra"
    assert info.name == "Foo Bar"
    assert info.uid == "5678"
    assert info.username == "Foo"


@patch.object(
    requests,
    "get",
    return_value=Mock(
        json=lambda: [
            {
                "email": "secondary@bar.com",
                "primary": False,
                "verified": True,
            },
            {
                "email": "primary@bar.com",
                "primary": True,
                "verified": True,
            },
        ]
    ),
)
def test_github_get_user_email_with_valid_email(mocked_request_get) -> None:
    helper = GitHubOauthHelper("code", "redirect_uri")
    helper.token = "token"

    email = helper.get_user_email()

    mocked_request_get.assert_called_once()
    assert email == "primary@bar.com"


@pytest.mark.parametrize(
    "mock_response",
    (
        [],
        [
            {
                "email": "not.primary@bar.com",
                "primary": False,
                "verified": True,
            },
            {
                "email": "not.primary@bar.com",
                "primary": False,
                "verified": True,
            },
        ],
        [
            {
                "email": "unverified.primary@bar.com",
                "primary": True,
                "verified": False,
            },
            {
                "email": "verified.secondary@bar.com",
                "primary": False,
                "verified": True,
            },
        ],
    ),
)
def test_github_get_user_email_without_valid_email(mock_response: List) -> None:
    helper = GitHubOauthHelper("code", "redirect_uri")
    helper.token = "token"

    with patch.object(requests, "get", return_value=Mock(json=lambda: mock_response)):
        with pytest.raises(Exception, match="User has no email available"):
            helper.get_user_email()


@pytest.mark.parametrize(
    ("provider", "expected"),
    (
        ("discord", DiscordOauthHelper),
        ("GiThUb", GitHubOauthHelper),
        ("acme", None),
    ),
)
def test_get_helper(provider: str, expected: Optional[BaseOauthHelper]) -> None:
    actual = get_helper(provider)

    assert type(actual) is type(expected)
