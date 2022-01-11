import pytest

from thunderstore.github.models.keys import KeyProvider


@pytest.mark.django_db
def test_key_provider_str(key_provider: KeyProvider):
    assert (
        key_provider.__str__()
        == f"Name: {key_provider.name} Provider URL: {key_provider.provider_url}"
    )
