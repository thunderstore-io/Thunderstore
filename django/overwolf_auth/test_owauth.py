from unittest.mock import patch

import pytest
from django.test import override_settings
from jwt import PyJWKClientError
from social_core.exceptions import AuthException  # type: ignore

from overwolf_auth.backends import OverwolfOAuth2, UserDetails
from overwolf_auth.cached_jwk_client import CachedJWKClient

ID_TOKEN = {
    "sub": "potato",
    "nickname": "fry",
    "picture": "https://upload.wikimedia.org/wikipedia/commons/0/02/Potato_with_sprouts.jpg",
    "preferred_username": "fry",
    "email": "fry@example.org",
    "email_verified": True,
}


@patch.object(OverwolfOAuth2, "_decode_response_jwt", return_value=ID_TOKEN)
def test_extra_data_is_returned(mocked_decode) -> None:
    extra_data = OverwolfOAuth2().extra_data(None, None, {})

    assert extra_data["email_verified"] == ID_TOKEN["email_verified"]
    assert extra_data["nickname"] == ID_TOKEN["nickname"]
    assert extra_data["picture"] == ID_TOKEN["picture"]
    assert extra_data["preferred_username"] == ID_TOKEN["preferred_username"]


@patch.object(OverwolfOAuth2, "_decode_response_jwt", return_value=ID_TOKEN)
def test_get_user_id_reads_correct_field(mocked_decode) -> None:
    details: UserDetails = {
        "username": "potato",
        "email": "fry@example.org",
        "fullname": "",
        "first_name": "",
        "last_name": "",
    }
    user_id = OverwolfOAuth2().get_user_id(details, {})

    assert user_id == details["username"]


@patch.object(OverwolfOAuth2, "_decode_response_jwt", return_value={})
def test_get_user_details_fails_on_missing_username(mocked_decode) -> None:
    with pytest.raises(AuthException) as exception_info:
        OverwolfOAuth2().get_user_details({})

    assert exception_info.value.backend == "JWT contained no username (sub)"


@patch.object(OverwolfOAuth2, "_decode_response_jwt", return_value=ID_TOKEN)
def test_get_user_details_returns_correct_data(mocked_decode) -> None:
    data = OverwolfOAuth2().get_user_details({})

    assert data["username"] == ID_TOKEN["sub"]
    assert data["email"] == ID_TOKEN["email"]
    assert data["fullname"] == ""
    assert data["first_name"] == ""
    assert data["last_name"] == ""


def test__decode_response_jwt_fails_on_missing_id_token() -> None:
    with pytest.raises(AuthException) as exception_info:
        OverwolfOAuth2()._decode_response_jwt({})

    assert exception_info.value.backend == "No id_token in auth response"


@override_settings(SOCIAL_AUTH_OVERWOLF_KEY="test")
@patch.object(CachedJWKClient, "clear_cache")
def test_cached_jwt_client_refetches_jwk_on_error(mocked_clear_cache) -> None:
    def args_storage_wrapper(func):
        """
        Wrapper for keeping records with what arguments a function was
        called with. Using the patch() method with a function that
        recursively calls itself seemed to lead to a situation where
        only the latest function call was stored.
        """

        def wrapper(*args, **kwargs):
            wrapper.call_args_list.append(args)
            return func(*args, **kwargs)

        wrapper.call_args_list = []
        return wrapper

    from overwolf_auth import cached_jwk_client

    wrapped_func = args_storage_wrapper(cached_jwk_client.decode_jwt)

    # Rubbish, decoding this will always fail.
    broken_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiSm9obiBEb2UifQ.DjwRE2jZhren2Wt37t5hlVru6Myq4AhpGLiiefF69u8"

    with patch("overwolf_auth.cached_jwk_client.decode_jwt", new=wrapped_func):
        with pytest.raises(PyJWKClientError):
            cached_jwk_client.decode_jwt(broken_jwt, False)

        # When the client fails the first time, it should clear the
        # cache and call itself recursively with reraise flag set to
        # True. Due to broken JWT, this will also fail.
        assert len(wrapped_func.call_args_list) == 2
        assert wrapped_func.call_args_list[0] == (broken_jwt, False)
        assert wrapped_func.call_args_list[1] == (broken_jwt, True)

    # Cached JWK client should clear the cache whenever decoding a JWT fails.
    mocked_clear_cache.call_count == 2
