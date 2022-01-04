import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_exception

from thunderstore.special.models.keys import KeyProvider, KeyType
from thunderstore.special.utils import setup_public_key, solve_key


class SecretScanningEndpoint(APIView):
    """
    Endpoint for receiving Githubs secret scanning matches
    """

    def __init__(self, **kwargs: Any) -> None:
        # Exclude this from the API documentation
        self.schema = None
        super().__init__(**kwargs)

    def post(self, request, format=None, provider_name="github_secret_scanning"):
        try:
            provider = KeyProvider.objects.get(name=provider_name)
        except KeyProvider.DoesNotExist as exc:
            capture_exception(exc)
            return Response(status=200)
        public_key = None
        signature = None
        key_identifier = request.headers["Github-Public-Key-Identifier"]
        signature = request.headers["Github-Public-Key-Signature"]
        # Assuming there is only one token per request
        request_json = json.loads(request.body)[0]
        token = request_json["token"]
        # TODO: TBD on what to do with these, github might send us the ec type or something have not seen it yet
        token_type = request_json["type"]
        token_url = request_json["url"]

        try:
            stored_public_key = solve_key(
                key_identifier=key_identifier,
                key_type=KeyType.SECP256R1,
                provider=provider,
            )
            public_key = setup_public_key(stored_public_key)
            public_key.verify(signature.encode(), token.encode(), ECDSA(SHA256()))
            # At this point we can do notifications or whatever, when a True positive is found
            return Response(status=200)
        except Exception as exc:
            capture_exception(exc)
            return Response(status=200)
