from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.user import (
    delete_user_account,
    delete_user_social_auth,
)
from thunderstore.api.utils import conditional_swagger_auto_schema

User = get_user_model()


@method_decorator(
    name="delete",
    decorator=conditional_swagger_auto_schema(
        responses={status.HTTP_204_NO_CONTENT: None},
        operation_id="cyberstorm.user.delete",
        tags=["cyberstorm"],
    ),
)
class DeleteUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        delete_user_account(target_user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(
    name="delete",
    decorator=conditional_swagger_auto_schema(
        responses={status.HTTP_204_NO_CONTENT: None},
        operation_id="cyberstorm.user.linked_account.disconnect",
        tags=["cyberstorm"],
    ),
)
class DisconnectUserLinkedAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, provider: str, *args, **kwargs):
        social_auth = request.user.social_auth.filter(provider=provider).first()
        if not social_auth:
            raise Http404("No linked account found")

        delete_user_social_auth(social_auth=social_auth)
        return Response(status=status.HTTP_204_NO_CONTENT)
