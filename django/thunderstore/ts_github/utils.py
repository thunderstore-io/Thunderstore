import base64
import hashlib
import json
from typing import List, Union

import requests
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_der_public_key
from pydantic import BaseModel, parse_obj_as
from sentry_sdk import capture_exception

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import hash_service_account_api_token
from thunderstore.ts_github.models.keys import KeyProvider, KeyType, StoredPublicKey


class KeyUpdateException(Exception):
    pass


class PrimitiveKey(BaseModel):
    key_identifier: str
    key: str
    is_current: bool


def process_primitive_key(primitive_key: PrimitiveKey, provider: KeyProvider):
    stored_key = StoredPublicKey.objects.filter(
        provider=provider,
        key_identifier=primitive_key.key_identifier,
    ).first()

    if stored_key:
        if stored_key.key != primitive_key.key:
            capture_exception(
                KeyUpdateException(
                    f"Provider identifier: {provider.identifier} Key Identifier: {stored_key.key_identifier} Error: key value {primitive_key.key} does not match the old one associated with the same key_identifier {stored_key.key} "
                )
            )
    else:
        StoredPublicKey.objects.create(
            provider=provider,
            key_identifier=primitive_key.key_identifier,
            key_type=KeyType.SECP256R1,
            key=primitive_key.key,
            is_active=primitive_key.is_current,
        )


def update_keys(provider: KeyProvider):
    primitive_keys = parse_obj_as(
        List[PrimitiveKey],
        requests.request("GET", provider.provider_url).json().get("public_keys"),
    )

    for primitive_key in primitive_keys:
        process_primitive_key(primitive_key, provider)

    provider.record_update_timestamp()


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
    # TODO: Do something when true positive is found
    pass


def build_response_data(token: str, type: str, positive_match: str):
    return {
        "token_hash": hashlib.sha256(token),
        "token_type": type,
        "label": positive_match,
    }
