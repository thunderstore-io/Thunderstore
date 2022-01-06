import base64
from datetime import timedelta
from typing import Generator

import pytest

from thunderstore.special.models.keys import KeyProvider, KeyType, StoredPublicKey
from thunderstore.special.utils import KeyUpdateException, solve_key, unpem, update_keys


@pytest.mark.django_db
@pytest.mark.parametrize("key_exists", (True, False))
@pytest.mark.parametrize("key_is_active", (True, False))
@pytest.mark.parametrize("key_key", ("FETCHED_TEST_KEY", "OLD_TEST_KEY"))
def test_update_keys(
    key_provider: KeyProvider,
    http_server_for_provider_keys: Generator[str, None, None],
    key_exists,
    key_is_active,
    key_key,
):
    if key_exists:
        stored_key = StoredPublicKey.objects.create(
            provider=key_provider,
            key_identifier="FETCHED_KEY_IDENTIFIER",
            key_type=KeyType.SECP256R1,
            key=key_key,
            is_active=key_is_active,
        )
    if key_key == "OLD_TEST_KEY" and key_exists:
        with pytest.raises(KeyUpdateException) as exc:
            update_keys(key_provider)
        assert (
            f"Provider: {key_provider.name} Key Identifier: {stored_key.key_identifier} Error: key value FETCHED_TEST_KEY does not match the old one {stored_key.key}"
            in str(exc.value)
        )
    elif key_exists:
        assert StoredPublicKey.objects.filter(
            provider=key_provider,
            key_identifier="FETCHED_KEY_IDENTIFIER",
            key=key_key,
        ).exists()


@pytest.mark.django_db
def test_solve_key(
    key_provider,
    stored_public_key,
    http_server_for_provider_keys: Generator[str, None, None],
):
    solved_key = solve_key(
        stored_public_key.key_identifier, KeyType.SECP256R1, key_provider
    )
    assert solved_key == stored_public_key
    key_provider.last_update_time = key_provider.last_update_time - timedelta(hours=25)
    key_provider.save()
    solved_key = solve_key(
        stored_public_key.key_identifier, KeyType.SECP256R1, key_provider
    )
    assert solved_key == stored_public_key
    assert StoredPublicKey.objects.filter(
        provider=key_provider,
        key_identifier="FETCHED_KEY_IDENTIFIER",
        key="FETCHED_TEST_KEY",
    ).exists()


@pytest.mark.django_db
def test_unpem():
    test_text = "-----BEGIN PUBLIC KEY-----\ndGVzdHRlc3R0ZXN0\ndGVzdHRlc3R0ZXN0\n-----END PUBLIC KEY-----\n"
    expected_result = base64.b64decode("dGVzdHRlc3R0ZXN0dGVzdHRlc3R0ZXN0".encode())
    result = unpem(test_text)
    assert expected_result == result
