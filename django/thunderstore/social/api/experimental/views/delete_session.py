from typing import Sequence, Type

from django.contrib.sessions.models import Session
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.social.permissions import OauthSharedSecretPermission


class DeleteSessionRequestBody(serializers.Serializer):
    sessionid = serializers.CharField(label="Thunderstore session key")


class DeleteSessionApiView(APIView):
    """
    Drop provided session from database.
    """

    permission_classes: Sequence[Type[BasePermission]] = [OauthSharedSecretPermission]

    @swagger_auto_schema(
        operation_id="experimental.auth.delete",
        request_body=DeleteSessionRequestBody,
        responses={204: ""},
    )
    def post(self, request: Request) -> HttpResponse:
        request_data = DeleteSessionRequestBody(data=request.data)
        request_data.is_valid(raise_exception=True)
        sessionid: str = request_data.validated_data["sessionid"]

        Session.objects.filter(session_key=sessionid).delete()
        return Response(status=204)
