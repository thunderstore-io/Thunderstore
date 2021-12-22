import binascii
import json

from cryptography.hazmat.primitives._serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.hashes import SHA256
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from sentry_sdk import capture_exception

from thunderstore.security.utils import fetch_and_setup_public_key


@csrf_exempt
@require_POST
def secret_scanning_endpoint(request):
    public_key = None
    signature = None
    data = None
    key_identifier = request.headers["Github-Public-Key-Identifier"]
    signature = request.headers["Github-Public-Key-Signature"]
    # Assuming there is only one token per request
    request_json = json.loads(request.body)[0]
    token = request_json["token"]
    token_type = request_json["type"]
    token_url = request_json["url"]

    try:
        public_key = fetch_and_setup_public_key(key_identifier)
        # print(binascii.hexlify(public_key.public_bytes(Encoding.X962, PublicFormat.CompressedPoint)))
        public_key.verify(signature, token, ECDSA(SHA256()))
        return HttpResponse(status=200)
    except Exception as exc:
        raise exc
        # capture_exception(exc)
