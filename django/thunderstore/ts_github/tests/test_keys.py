import pytest

from thunderstore.ts_github.models.keys import KeyProvider, StoredPublicKey


@pytest.mark.django_db
def test_key_provider_str(key_provider: KeyProvider):
    assert (
        str(key_provider)
        == f"Provider identifier: {key_provider.identifier} Provider URL: {key_provider.provider_url}"
    )


@pytest.mark.django_db
def test_stored_public_key_str(stored_public_key: StoredPublicKey):
    assert str(stored_public_key) == f"Identifier: {stored_public_key.key_identifier}"
