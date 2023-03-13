from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache
from jwt import (
    InvalidAlgorithmError,
    InvalidSignatureError,
    PyJWKClient,
    PyJWKClientError,
)
from jwt import decode as jwt_decode
from jwt.api_jwk import PyJWK

CACHE_KEY = "overwolf-oauth-jwks"
JWKS_URL = "https://accounts.overwolf.com/oauth2/jwks.json"


class CachedJWKClient(PyJWKClient):
    """
    Based on https://github.com/jpadilla/pyjwt/issues/615#issuecomment-817875411

    Targets pyjwt v2.0.1.
    """

    def __init__(self, uri: str):
        super().__init__(uri)

    def fetch_data(self) -> Any:
        # No auto expiration, manual expiration only
        return cache.get_or_set(CACHE_KEY, super().fetch_data, timeout=None)


def get_jwt_signing_key(token: str) -> PyJWK:
    return CachedJWKClient(JWKS_URL).get_signing_key_from_jwt(token)


def decode_jwt(token: str, reraise=False) -> Dict[str, str]:
    try:
        signing_key = get_jwt_signing_key(token)

        return jwt_decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.SOCIAL_AUTH_OVERWOLF_KEY,
        )
    except (InvalidSignatureError, InvalidAlgorithmError, PyJWKClientError) as e:
        # Always invalidate the cache since the signature we are getting
        # back is clearly invalid.
        cache.delete(CACHE_KEY)

        if reraise:
            raise e

        # Assume the JWKs changed and these are no longer valid, retry
        # again now that we have deleted the cache to grab a new set.
        # If it still fails, re-raise to alert us.
        return decode_jwt(token, True)
