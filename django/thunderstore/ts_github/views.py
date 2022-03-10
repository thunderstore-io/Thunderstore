import json
from typing import Any

from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models import ServiceAccount
from thunderstore.ts_github.models.keys import KeyProvider, KeyType
from thunderstore.ts_github.utils import (
    build_response_data,
    get_service_account,
    handle_true_positive_match,
    verify_key,
)


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
        try:
            verify_key(
                KeyType.SECP256R1,
                KeyProvider.objects.get(identifier=provider_identifier),
                request.headers["Github-Public-Key-Identifier"],
                request.headers["Github-Public-Key-Signature"],
                request.body,
            )
        except:
            return Response(status=404)

        response_data = []

        for token in json.loads(request.body):
            sa = get_service_account(token["token"])
            if isinstance(sa, ServiceAccount):
                handle_true_positive_match(sa, token["url"])
                positive_match = "true_positive"
            else:
                positive_match = "false_positive"
            response_data.append(
                build_response_data(token["token"], token["type"], positive_match)
            )
        return Response(response_data, status=200, content_type="application/json")
