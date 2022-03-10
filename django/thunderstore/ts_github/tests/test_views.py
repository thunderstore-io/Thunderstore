import base64
import hashlib
from unittest import mock

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, EllipticCurvePrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from django.test import Client
from rest_framework.test import APIClient

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)
from thunderstore.community.models.community_site import CommunitySite
from thunderstore.ts_github.models.keys import StoredPublicKey
from thunderstore.ts_github.views import SecretScanningEndpoint


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
    response = endpoint.post(mock_request, provider_identifier="wrong_provider")
    assert response.status_code == 404
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


@pytest.mark.django_db
@pytest.mark.parametrize("service_account_exists", (True, False))
def test_secret_scanning_endpoint_post_through_url_routing(
    community_site: CommunitySite,
    ec_private_key: EllipticCurvePrivateKey,
    stored_public_key: StoredPublicKey,
    service_account: ServiceAccount,
    service_account_exists: bool,
):
    c = Client()
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

    # Test success
    signature = ec_private_key.sign(payload, ECDSA(SHA256()))
    response = c.post(
        "/_/github/secret-scanning/validate/",
        payload,
        content_type="application/json",
        HTTP_GITHUB_PUBLIC_KEY_IDENTIFIER="TEST_IDENTIFIER",
        HTTP_GITHUB_PUBLIC_KEY_SIGNATURE=base64.b64encode(signature),
        HTTP_HOST="testsite.test",
    )
    assert response.status_code == 200
    assert (
        response.content
        == (
            '[{"token_hash":"%s","token_type":"TEST_TOKEN_TYPE","label":"%s"}]'
            % (
                hashlib.sha256(new_token.encode()).hexdigest(),
                "true_positive" if service_account_exists else "false_positive",
            )
        ).encode()
    )

    # Test bad signature
    response = c.post(
        "/_/github/secret-scanning/validate/",
        payload,
        content_type="application/json",
        HTTP_GITHUB_PUBLIC_KEY_IDENTIFIER="TEST_IDENTIFIER",
        HTTP_GITHUB_PUBLIC_KEY_SIGNATURE="BAD_SIGNATURE",
        HTTP_HOST="testsite.test",
    )
    assert response.status_code == 404

    stored_public_key.key = "BAD_KEY"
    stored_public_key.save()
    # Test bad public key fail
    response = c.post(
        "/_/github/secret-scanning/validate/",
        payload,
        content_type="application/json",
        HTTP_GITHUB_PUBLIC_KEY_IDENTIFIER="TEST_IDENTIFIER",
        HTTP_GITHUB_PUBLIC_KEY_SIGNATURE=base64.b64encode(signature),
        HTTP_HOST="testsite.test",
    )
    assert response.status_code == 404
