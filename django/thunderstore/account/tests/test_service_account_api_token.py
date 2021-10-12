import re
from datetime import datetime

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from thunderstore.account.authentication import ServiceAccountTokenAuthentication
from thunderstore.account.factories import ServiceAccountFactory
from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)


def test_hash_parameters_are_fixed():
    hashed = hash_service_account_api_token("somevalue")
    (hasher, iterations, salt, hashed) = hashed.split("$")
    assert hasher == "pbkdf2_sha256"
    assert iterations == "524288"
    assert salt == "w520TEzFVlsO"
    assert len(hashed) == 44


def test_token_format():
    payload_chars = re.compile("[A-Za-z0-9]+")

    for _ in range(10):
        token = get_service_account_api_token()
        assert len(token) == 40
        assert token.startswith("tss_")
        assert payload_chars.fullmatch(token[4:]) is not None


@pytest.mark.django_db
def test_api_token_authentication_is_passed_when_no_header():
    """
    If no header is provided, return None signaling that other
    configured authentication methods should be tried.
    """
    request = RequestFactory().get("")
    assert ServiceAccountTokenAuthentication().authenticate(request) is None


@pytest.mark.django_db
def test_api_token_authentication_is_passed_with_non_bearer_token():
    request = RequestFactory().get("", HTTP_AUTHORIZATION="Session foo123")
    assert ServiceAccountTokenAuthentication().authenticate(request) is None


@pytest.mark.django_db
def test_api_token_authentication_requires_existing_token():
    real_token = get_service_account_api_token()
    ServiceAccountFactory(plaintext_token=real_token)
    fake_token = get_service_account_api_token()

    request_token = f"Bearer {fake_token}"
    request = RequestFactory().get("", HTTP_AUTHORIZATION=request_token)

    with pytest.raises(AuthenticationFailed) as e:
        ServiceAccountTokenAuthentication().authenticate(request)

    assert str(e.value) == "Invalid Service Account token"


@pytest.mark.django_db
def test_api_token_authentication_is_successful():
    real_token = get_service_account_api_token()
    sa = ServiceAccountFactory(plaintext_token=real_token)

    request_token = f"Bearer {real_token}"
    request = RequestFactory().get("", HTTP_AUTHORIZATION=request_token)
    (user, token) = ServiceAccountTokenAuthentication().authenticate(request)

    assert user == sa.user
    assert token == real_token


@pytest.mark.django_db
def test_service_account_token_last_used(api_client):
    real_token = get_service_account_api_token()
    sa = ServiceAccountFactory(plaintext_token=real_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {real_token}")

    # First use should change last_used from None to datetime.
    response = api_client.get(
        "/api/experimental/current-user/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert "capabilities" in response.content.decode()
    sa_obj1 = ServiceAccount.objects.get(pk=sa.uuid)
    assert sa_obj1.created_at == sa.created_at
    assert isinstance(sa_obj1.last_used, datetime)

    # Second use should update last_used.
    response = api_client.get(
        "/api/experimental/current-user/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert "capabilities" in response.content.decode()
    sa_obj2 = ServiceAccount.objects.get(pk=sa.uuid)
    assert sa_obj2.created_at == sa.created_at
    assert isinstance(sa_obj2.last_used, datetime)
    assert sa_obj2.last_used > sa_obj1.last_used
