from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.social.views import (
    DeleteAccountForm,
    LinkedAccountDisconnectExecption,
    LinkedAccountDisconnectForm,
)


class CyberstormException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Issue occured when trying to process action")
    default_code = "error"


class CyberstormUserDeleteRequestSerialiazer(serializers.Serializer):
    verification = serializers.CharField()


class CyberstormUserDeleteResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField()


class UserDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormUserDeleteRequestSerialiazer,
        responses={200: CyberstormUserDeleteResponseSerialiazer},
        operation_id="cyberstorm.current-user.delete",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest):
        serializer = CyberstormUserDeleteRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = DeleteAccountForm(
            user=request.user,
            data=serializer.validated_data,
        )
        if form.is_valid():
            form.delete_user()
            return Response()
        else:
            raise ValidationError(form.errors)


class CyberstormUserDisconnectProviderRequestSerialiazer(serializers.Serializer):
    provider = serializers.CharField()


class CyberstormUserDisconnectProviderResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField()
    provider = serializers.CharField()


class UserLinkedAccountDisconnectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormUserDisconnectProviderRequestSerialiazer,
        responses={200: CyberstormUserDisconnectProviderResponseSerialiazer},
        operation_id="cyberstorm.current-user.linked-account-disconnect",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest):
        serializer = CyberstormUserDisconnectProviderRequestSerialiazer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        form = LinkedAccountDisconnectForm(
            user=request.user,
            data=serializer.validated_data,
        )
        if form.is_valid():
            try:
                form.disconnect_account(with_raise=True)
            except LinkedAccountDisconnectExecption as e:
                raise CyberstormException(detail=e)
            return Response(
                CyberstormUserDisconnectProviderResponseSerialiazer(
                    {
                        "username": request.user.username,
                        "provider": serializer.validated_data["provider"],
                    }
                ).data
            )
        else:
            raise ValidationError(form.errors)
