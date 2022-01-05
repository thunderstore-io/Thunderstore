import base64
import binascii
import datetime
import json

import requests
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.asymmetric import ec
from django.utils import timezone

from thunderstore.special.models.keys import KeyType, StoredPublicKey


class KeyUpdateException(Exception):
    ...


def update_keys(provider):
    public_key_endpoint = requests.request("GET", provider.provider_url)
    for k in json.loads(public_key_endpoint.content)["public_keys"]:
        stored_key, created = StoredPublicKey.objects.get_or_create(
            provider=provider, key_identifier=k["key_identifier"]
        )
        if not created:
            if stored_key.key != k["key"]:
                raise KeyUpdateException(
                    f"Provider: {provider.name} Key Identifier: {stored_key.key_identifier} Error: key value does not match the old one"
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

    provider.last_update_time = timezone.now()
    provider.save()


def solve_key(key_identifier, key_type, provider):
    if (timezone.now() - provider.last_update_time) > datetime.timedelta(hours=24):
        update_keys(provider)
    return StoredPublicKey.objects.get(
        provider=provider,
        key_identifier=key_identifier,
        key_type=key_type,
        is_active=True,
    )


def unpem(pem):
    pem_data = pem.encode() if isinstance(pem, str) else pem

    d = (b"").join(
        [l.strip() for l in pem_data.split(b"\n") if l and not l.startswith(b"-----")]
    )
    return base64.b64decode(d)
