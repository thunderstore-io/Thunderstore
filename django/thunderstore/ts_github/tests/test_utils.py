import base64
import hashlib

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256

from thunderstore.account.models import ServiceAccount
from thunderstore.ts_github.models.keys import (
    KeyProvider,
    KeyType,
    PrimitiveKey,
    StoredPublicKey,
)
from thunderstore.ts_github.utils import (
    build_response_data,
    get_service_account,
    process_primitive_key,
    unpem,
    update_keys,
    verify_key,
)


@pytest.mark.django_db
def test_process_primitive_key_new_key(primitive_key: PrimitiveKey, key_provider):
    process_primitive_key(primitive_key, key_provider)
    processed_key = StoredPublicKey.objects.get(
        key_identifier=primitive_key.key_identifier
    )
    assert processed_key.provider == key_provider
    assert processed_key.key_identifier == primitive_key.key_identifier
    assert processed_key.key_type == KeyType.SECP256R1
    assert processed_key.key == primitive_key.key
    assert processed_key.is_active == primitive_key.is_current


@pytest.mark.django_db
def test_update_keys(
    key_provider: KeyProvider,
):
    update_keys(key_provider)
    updated_key = StoredPublicKey.objects.get(key_identifier="FETCHED_KEY_IDENTIFIER")
    assert updated_key.provider == key_provider
    assert updated_key.key_identifier == "FETCHED_KEY_IDENTIFIER"
    assert updated_key.key_type == KeyType.SECP256R1
    assert updated_key.key == "FETCHED_TEST_KEY"
    assert updated_key.is_active == True


@pytest.mark.django_db
def test_unpem():
    test_text = "-----BEGIN PUBLIC KEY-----\ndGVzdHRlc3R0ZXN0\ndGVzdHRlc3R0ZXN0\n-----END PUBLIC KEY-----\n"
    expected_result = base64.b64decode("dGVzdHRlc3R0ZXN0dGVzdHRlc3R0ZXN0".encode())
    result = unpem(test_text)
    assert expected_result == result


@pytest.mark.django_db
def test_verify_key(team, key_provider, stored_public_key, ec_private_key):
    service_account, token = ServiceAccount.create(team, "TEST")
    data = (
        '[{"token":"%s","type":"TEST_TOKEN_TYPE","url":"example.com"}]' % token
    ).encode()

    # Test success
    signature = ec_private_key.sign(data, ECDSA(SHA256()))
    verify_key(
        KeyType.SECP256R1,
        key_provider,
        stored_public_key.key_identifier,
        base64.b64encode(signature),
        data,
    )

    # Test bad signature fail
    bad_signature = ec_private_key.sign(data + "BAD_SIGN".encode(), ECDSA(SHA256()))
    with pytest.raises(InvalidSignature):
        verify_key(
            KeyType.SECP256R1,
            key_provider,
            stored_public_key.key_identifier,
            base64.b64encode(bad_signature),
            data,
        )

    # Test bad public key fail
    stored_public_key.key = "BAD_PUBLIC_KEY"
    stored_public_key.save()

    with pytest.raises(ValueError) as e:
        verify_key(
            KeyType.SECP256R1,
            key_provider,
            stored_public_key.key_identifier,
            base64.b64encode(signature),
            data,
        )
    assert (
        str(e.value)
        == "Could not deserialize key data. The data may be in an incorrect format or it may be encrypted with an unsupported algorithm."
    )


@pytest.mark.django_db
def test_get_service_account(team):
    assert get_service_account("FAKE_TOKEN") == None
    service_account, token = ServiceAccount.create(team, "TEST")
    assert get_service_account(token)


@pytest.mark.django_db
def test_build_response_data(team):
    service_account, token = ServiceAccount.create(team, "TEST")
    response_data = build_response_data(
        token,
        "test_token_type",
        "true_positive",
    )
    assert response_data["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert response_data["token_type"] == "test_token_type"
    assert response_data["label"] == "true_positive"
