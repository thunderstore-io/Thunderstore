from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from rest_framework.views import APIView


class ValidateSessionApiView(APIView):
    """
    Check that valid session key is provided in Authorization header.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id="experimental.auth.validate",
        responses={
            200: "Session is valid",
            401: "Session key is missing, invalid, or expired",
        },
        deprecated=True,
        tags=["experimental"],
    )
    def get(self, request: Request) -> HttpResponse:
        # UserSessionTokenAuthentication will automatically return 401
        # if the given session key is not valid, but will do nothing if
        # the session key isn't provided at all.
        if request.user.is_authenticated:
            return Response({"detail": "OK"})

        return Response({"detail": "Invalid token."}, HTTP_401_UNAUTHORIZED)
