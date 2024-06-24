from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.social.views import DeleteAccountForm


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
