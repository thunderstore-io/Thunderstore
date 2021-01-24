import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.parsers import BaseParser
from rest_framework.views import APIView

from thunderstore.core.models import IncomingJWTAuthConfiguration


class JWTAuthentication(BaseAuthentication):
    """
    Authenticates JWT data
    """

    def authenticate(self, request):
        jwt_data = request.data

        try:
            header = jwt.get_unverified_header(jwt_data)
        except jwt.exceptions.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid JWT token format")

        key_id = header.get("kid")

        if key_id is None:
            raise exceptions.AuthenticationFailed("Missing key ID JWT header")

        try:
            result = IncomingJWTAuthConfiguration.decode_incoming_data(jwt_data, key_id)
        except jwt.exceptions.InvalidTokenError:
            raise exceptions.AuthenticationFailed("JWT Verification failed")

        request.decoded = result["data"]
        return (result["user"], None)


class JWTParser(BaseParser):
    """
    Parses JWT data
    """

    media_type = "application/jwt"

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parsing will be handled by the authentication part,
        so simply pass the content forward
        """
        return stream.read()


class JWTApiView(APIView):
    """
    API View intended to be used for receiving JWT requets
    """

    authentication_classes = [JWTAuthentication]
    parser_classes = [JWTParser]
