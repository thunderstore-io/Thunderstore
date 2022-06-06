from typing import Sequence, Type
from uuid import uuid4

from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.core.types import UserType
from thunderstore.social.permissions import OauthSharedSecretPermission
from thunderstore.social.providers import UserInfoSchema, get_helper

User = get_user_model()


class RequestBody(serializers.Serializer):
    code = serializers.CharField(
        label="Authorization code received from the provider when authentication flow was initiated on the client"
    )
    redirect_uri = serializers.CharField(
        label="Redirect URI used when the authentication flow was initiated on client"
    )


class ResponseBody(serializers.Serializer):
    email = serializers.CharField(allow_null=True)
    session_id = serializers.CharField()
    username = serializers.CharField()


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

        helper = helper_class(code, redirect_uri)
        helper.complete_login()
        user_info = helper.get_user_info()
        user = get_or_create_auth_user(user_info)
        login(request, user, "django.contrib.auth.backends.ModelBackend")

        return Response(
            {
                "email": user.email,
                "session_id": request.session.session_key,
                "username": user.username,
            }
        )


@transaction.atomic
def get_or_create_auth_user(user_info: UserInfoSchema) -> UserType:
    """
    Return local user object based on OAuth user data.

    The "local" user object is the one defined in Django config.
    social_django library manages additional OAuth related data via
    UserSocialAuth model.
    """
    try:
        sa_user: UserSocialAuth = UserSocialAuth.objects.get(
            provider=user_info.provider,
            uid=user_info.uid,
        )
    except UserSocialAuth.DoesNotExist:
        username = get_unique_username(user_info.username)
        full = user_info.name
        first, last = full.split(" ", 1) if " " in full else (full, "")

        user = User(
            email=user_info.email,
            first_name=first,
            last_name=last,
            username=username,
        )
        user.set_unusable_password()  # type: ignore
        user.save()

        sa_user = UserSocialAuth.objects.create(
            extra_data=user_info.extra_data,
            provider=user_info.provider,
            uid=user_info.uid,
            user=user,
        )
    else:
        sa_user.extra_data = user_info.extra_data
        sa_user.save()

    return sa_user.user


def get_unique_username(original_username: str) -> str:
    """
    Add random suffix to username when needed to make it unique.

    This imitates how Social Auth library implements a similar method,
    minus all the configurability.
    """
    if original_username == "":
        raise ValueError("Username may not be empty")

    max_length = User._meta.get_field("username").max_length or 150
    suffix_length = 16
    slugified = slugify(original_username)[:max_length]
    username = slugified
    attempts_remaining = 10  # Prevent infinite loops in case of bugs.

    while attempts_remaining and User.objects.filter(username=username).exists():
        suffix = uuid4().hex[:suffix_length]
        username = slugified[: (max_length - suffix_length)] + suffix
        attempts_remaining -= 1

    return username
