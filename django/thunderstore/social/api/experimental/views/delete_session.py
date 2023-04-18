from typing import Sequence, Type

from django.contrib.sessions.models import Session
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class DeleteSessionApiView(APIView):
    """
    Drop provided session from database.

    The session is provided in Authorization header and is processed by
    UserSessionTokenAuthentication, which places the session key into
    request.auth.
    """

    permission_classes: Sequence[Type[BasePermission]] = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="experimental.auth.delete",
        responses={204: ""},
    )
    def post(self, request: Request) -> HttpResponse:
        Session.objects.filter(session_key=request.auth).delete()
        return Response(status=204)
