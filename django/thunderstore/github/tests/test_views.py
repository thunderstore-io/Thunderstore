import base64
from unittest import mock

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, EllipticCurvePrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from rest_framework.test import APIClient

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)
from thunderstore.github.models.keys import KeyProvider, StoredPublicKey
from thunderstore.github.views import SecretScanningEndpoint


@pytest.mark.django_db
@pytest.mark.parametrize("service_account_exists", (True, False))
def test_secret_scanning_endpoint_post_function(
    ec_private_key: EllipticCurvePrivateKey,
    stored_public_key: StoredPublicKey,
    service_account: ServiceAccount,
    service_account_exists: bool,
):
    clash = True
    while clash:
        new_token = get_service_account_api_token()
        hashed = hash_service_account_api_token(new_token)
        clash = ServiceAccount.objects.filter(api_token=hashed).exists()
    if service_account_exists:
        service_account.api_token = hashed
        service_account.save()

    mock_request = mock.Mock(spec=requests.Request)
    payload = (
        '[{"token":"%s","type":"TEST_TOKEN_TYPE","url":"example.com"}]' % new_token
    ).encode()
    mock_request.body = payload
    signature = ec_private_key.sign(payload, ECDSA(SHA256()))
    mock_request.headers = {
        "content_type": "application/json",
        "Github-Public-Key-Identifier": "TEST_IDENTIFIER",
        "Github-Public-Key-Signature": base64.b64encode(signature),
    }
    endpoint = SecretScanningEndpoint()
    # Just test with non-existent provider
    with pytest.raises(KeyProvider.DoesNotExist):
        endpoint.post(mock_request, provider_name="wrong_provider")
    response = endpoint.post(mock_request)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("service_account_exists", (True, False))
def test_secret_scanning_endpoint_api_post(
    api_client: APIClient,
    ec_private_key: EllipticCurvePrivateKey,
    stored_public_key: StoredPublicKey,
    service_account: ServiceAccount,
    service_account_exists: bool,
):
    clash = True
    while clash:
        new_token = get_service_account_api_token()
        hashed = hash_service_account_api_token(new_token)
        clash = ServiceAccount.objects.filter(api_token=hashed).exists()
    if service_account_exists:
        service_account.api_token = hashed
        service_account.save()
    payload = (
        '[{"token":"%s","type":"TEST_TOKEN_TYPE","url":"example.com"}]' % new_token
    ).encode()
    signature = ec_private_key.sign(payload, ECDSA(SHA256()))
    response = api_client.post(
        "/_/github/secret-scanning/validate/",
        payload,
        content_type="application/json",
        HTTP_GITHUB_PUBLIC_KEY_IDENTIFIER="TEST_IDENTIFIER",
        HTTP_GITHUB_PUBLIC_KEY_SIGNATURE=base64.b64encode(signature),
    )
    assert response.status_code == 200
