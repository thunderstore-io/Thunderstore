import base64
from datetime import timedelta
from typing import Generator

import pytest

from thunderstore.special.models.keys import KeyProvider, KeyType, StoredPublicKey
from thunderstore.special.utils import solve_key, unpem, update_keys


@pytest.mark.django_db
def test_update_keys(
    key_provider: KeyProvider, http_server_for_provider_keys: Generator[str, None, None]
):
    update_keys(key_provider)
    assert StoredPublicKey.objects.filter(
        provider=key_provider,
        key_identifier="FETCHED_KEY_IDENTIFIER",
        key="FETCHED_TEST_KEY",
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
