from typing import Sequence, Type

from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from thunderstore.social.permissions import OauthSharedSecretPermission
from thunderstore.social.providers import get_helper


class RequestBody(serializers.Serializer):
    code = serializers.CharField(
        label="Authorization code received from the provider when authentication flow was initiated on the client"
    )
    redirect_uri = serializers.CharField(
        label="Redirect URI used when the authentication flow was initiated on client"
    )


class ResponseBody(serializers.Serializer):
    session_id = serializers.CharField()


class CompleteLoginApiView(APIView):
    """
    Complete OAuth login process initiated by a client.
    """

    permission_classes: Sequence[Type[BasePermission]] = [OauthSharedSecretPermission]

    @swagger_auto_schema(
        operation_id="experimental.auth.complete",
        request_body=RequestBody,
        responses={200: ResponseBody()},
    )
    def post(self, request: Request, provider: str) -> HttpResponse:
        request_data = RequestBody(data=request.data)
        request_data.is_valid(raise_exception=True)
        code: str = request_data.validated_data["code"]
        redirect_uri: str = request_data.validated_data["redirect_uri"]

        helper_class = get_helper(provider)
        if not helper_class:
            return Response("Unsupported OAuth provider", HTTP_400_BAD_REQUEST)

        # TODO: get or create a user account based on user_info, create
        # a new session for the user and return session id.
        helper = helper_class(code, redirect_uri)
        helper.complete_login()
        user_info = helper.get_user_info()

        return Response({"session_id": "TODO"})
