from typing import Any, Dict

import requests
from django.conf import settings
from jwt import (
    InvalidAlgorithmError,
    InvalidSignatureError,
    PyJWKClient,
    PyJWKClientError,
)
from jwt import decode as jwt_decode

from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition

CACHE_KEY = "overwolf-oauth-jwks"
JWKS_URL = "https://accounts.overwolf.com/oauth2/jwks.json"


@cache_function_result(CacheBustCondition.background_update_only)
def cached_json_fetch(url: str) -> Any:
    return requests.get(url).json()


class CachedJWKClient(PyJWKClient):
    """
    Based on https://github.com/jpadilla/pyjwt/issues/615#issuecomment-817875411

    Targets pyjwt v2.0.1.
    """

    def __init__(self, uri: str):
        super().__init__(uri)

    def fetch_data(self) -> Any:
        return cached_json_fetch(url=self.uri)

    def clear_cache(self):
        cached_json_fetch.clear_cache_with_args(url=self.uri)


jwk_client = CachedJWKClient(JWKS_URL)


def decode_jwt(token: str, reraise=False) -> Dict[str, str]:
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        return jwt_decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.SOCIAL_AUTH_OVERWOLF_KEY,
        )
    except (InvalidSignatureError, InvalidAlgorithmError, PyJWKClientError) as e:
        # Always invalidate the cache since the signature we are getting
        # back is clearly invalid.
        jwk_client.clear_cache()

        if reraise:
            raise e

        # Assume the JWKs changed and these are no longer valid, retry
        # again now that we have deleted the cache to grab a new set.
        # If it still fails, re-raise to alert us.
        return decode_jwt(token, True)
