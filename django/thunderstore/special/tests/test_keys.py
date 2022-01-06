import pytest


@pytest.mark.django_db
def test_key_provider_str(key_provider):
    assert (
        key_provider.__str__()
        == f"Name: {key_provider.name} Provider URL: {key_provider.provider_url}"
    )
