from typing import Sequence, Type

import requests
import ulid2  # type: ignore
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from pydantic import BaseModel
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.social.api.experimental.views.complete_login import (
    get_or_create_auth_user,
)
from thunderstore.social.api.experimental.views.current_user import (
    UserProfileSerializer,
    get_user_profile,
)
from thunderstore.social.permissions import ImproperlyConfigured
from thunderstore.social.providers import UserInfoSchema

User = get_user_model()


class OwLoginRequestBody(serializers.Serializer):
    jwt = serializers.CharField(label="Authorization token")


class OwLoginResponseBody(serializers.Serializer):
    session_id = serializers.CharField()
    profile = UserProfileSerializer()


class OverwolfProfileSchema(BaseModel):
    """
    https://overwolf.github.io/api/profile#get-user-profile-via-token
    """

    avatar: str
    nickname: str
    username: str


class OverwolfLoginApiView(APIView):
    """
    Login user with information from Overwolf API using the received JWT

    Used by Thunderstore Mod Manager. Not to be confused with OAuth
    login process triggered from a browser.
    """

    permission_classes: Sequence[Type[BasePermission]] = []

    @swagger_auto_schema(
        operation_id="experimental.auth.overwolf.login",
        request_body=OwLoginRequestBody,
        responses={200: OwLoginResponseBody()},
        tags=["experimental"],
    )
    def post(self, request: Request) -> HttpResponse:
        request_data = OwLoginRequestBody(data=request.data)
        request_data.is_valid(raise_exception=True)
        jwt: str = request_data.validated_data["jwt"]

        verify_overwolf_jwt(jwt)
        ow_profile = get_overwolf_user_profile(jwt)
        user_info = get_user_info(ow_profile)
        user = get_or_create_auth_user(user_info)
        login(request, user, "django.contrib.auth.backends.ModelBackend")

        if not request.session.session_key:
            request.session.create()

        return Response(
            {
                "session_id": request.session.session_key,
                "profile": get_user_profile(user),
            }
        )


def query_overwolf_jwt_api(path: str, jwt: str) -> requests.Response:
    ow_id = settings.OVERWOLF_CLIENT_ID

    if not ow_id:
        raise ImproperlyConfigured

    url = f"https://accounts.overwolf.com/tokens/short-lived/{path}?extensionId={ow_id}"
    headers = {"Authorization": f"Bearer {jwt}"}
    return requests.get(url, headers=headers)


def verify_overwolf_jwt(jwt: str) -> None:
    response = query_overwolf_jwt_api("verify", jwt)

    if response.status_code != 200:
        raise AuthenticationFailed("Invalid or expired JWT")


def get_overwolf_user_profile(jwt: str) -> OverwolfProfileSchema:
    response = query_overwolf_jwt_api("users/profile", jwt)
    return OverwolfProfileSchema.parse_obj(response.json())


def get_user_info(profile: OverwolfProfileSchema) -> UserInfoSchema:
    """
    Overwolf doesn't provide a way to query user's email address, so
    make one up, like we do for service accounts.
    """
    return UserInfoSchema.parse_obj(
        {
            "email": f"{ulid2.generate_ulid_as_uuid().hex}.mm@thunderstore.io",
            "extra_data": profile,
            "name": profile.nickname,
            "provider": "overwolf",
            "uid": profile.username,
            "username": profile.username,
        }
    )
