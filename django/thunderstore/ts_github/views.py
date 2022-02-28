import base64
import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_der_public_key
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import hash_service_account_api_token
from thunderstore.ts_github.models.keys import KeyProvider, KeyType
from thunderstore.ts_github.utils import solve_key, unpem


class SecretScanningEndpoint(APIView):
    """
    Endpoint for receiving Githubs secret scanning matches
    """

    def __init__(self, **kwargs: Any) -> None:
        # Exclude this from the API documentation
        self.schema = None
        super().__init__(**kwargs)

    def post(
        self, request, provider_identifier: str = "github_secret_scanning"
    ) -> Response:
        provider = KeyProvider.objects.get(identifier=provider_identifier)
        key_identifier = request.headers["Github-Public-Key-Identifier"]
        signature = request.headers["Github-Public-Key-Signature"]
        # Assuming there is only one token per request
        request_json = json.loads(request.body)[0]
        token = request_json["token"]
        # TODO: TBD on what to do with these, github might send us the ec type or something have not seen it yet
        token_type = request_json["type"]
        token_url = request_json["url"]

        stored_public_key = solve_key(
            key_identifier=key_identifier,
            key_type=KeyType.SECP256R1,
            provider=provider,
        )
        public_key = load_der_public_key(unpem(stored_public_key.key))
        public_key.verify(base64.b64decode(signature), request.body, ECDSA(SHA256()))
        hashed_payload_token = hash_service_account_api_token(token)
        if ServiceAccount.objects.filter(
            api_token__exact=hashed_payload_token
        ).exists():
            print("Yes is valid")
            # At this point we can do notifications or whatever, when a True positive is found
        else:
            print("Is no valid")
            # At this point we can ignore
        return Response(status=200)
