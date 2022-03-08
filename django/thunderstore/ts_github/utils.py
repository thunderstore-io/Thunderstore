import base64
import hashlib
import json
from typing import Union

import requests
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_der_public_key
from django.utils import timezone

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import hash_service_account_api_token
from thunderstore.ts_github.models.keys import KeyProvider, KeyType, StoredPublicKey


class KeyUpdateException(Exception):
    pass


def update_keys(provider: KeyProvider):
    public_key_endpoint = requests.request("GET", provider.provider_url)
    for k in json.loads(public_key_endpoint.content)["public_keys"]:
        stored_key, created = StoredPublicKey.objects.get_or_create(
            provider=provider, key_identifier=k["key_identifier"]
        )
        if not created:
            if stored_key.key != k["key"]:
                raise KeyUpdateException(
                    f"Provider identifier: {provider.identifier} Key Identifier: {stored_key.key_identifier} Error: key value {k['key']} does not match the old one {stored_key.key}"
                )
            if stored_key.is_active and k["is_current"] == "false":
                stored_key.is_active == False
                stored_key.save()
            elif not stored_key.is_active and k["is_current"] == "true":
                stored_key.is_active == True
                stored_key.save()
        else:
            stored_key.key = k["key"]
            stored_key.is_active = k["is_current"]
            stored_key.key_type = KeyType.SECP256R1
            stored_key.save()

    provider.datetime_last_synced = timezone.now()
    provider.save()


def unpem(pem: Union[str, bytes]) -> bytes:
    pem_data = pem.encode() if isinstance(pem, str) else pem

    d = (b"").join(
        [l.strip() for l in pem_data.split(b"\n") if l and not l.startswith(b"-----")]
    )
    return base64.b64decode(d)


def verify_key(
    key_type: str,
    provider: KeyProvider,
    key_identifier: str,
    signature: str,
    data: str,
):
    stored_public_key = StoredPublicKey.objects.get(
        provider=provider,
        key_identifier=key_identifier,
        key_type=key_type,
        is_active=True,
    )
    public_key = load_der_public_key(unpem(stored_public_key.key))
    public_key.verify(base64.b64decode(signature), data, ECDSA(SHA256()))


def get_service_account(token):
    hashed_payload_token = hash_service_account_api_token(token)
    try:
        return ServiceAccount.objects.get(api_token__exact=hashed_payload_token)
    except ServiceAccount.DoesNotExist:
        return None


def handle_true_positive_match(service_account: ServiceAccount, commit_url: str):
    # Do something when true positive is found
    pass


def build_response_data(token: str, type: str, positive_match: str):
    return {
        "token_hash": hashlib.sha256(token),
        "token_type": type,
        "label": positive_match,
    }
