from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers.user import (
    CyberstormAccountDeleteRequestSerialiazer,
    CyberstormAccountDeleteResponseSerialiazer,
)
from thunderstore.social.views import DeleteAccountForm


class UserDeleteAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormAccountDeleteRequestSerialiazer,
        responses={200: CyberstormAccountDeleteResponseSerialiazer},
        operation_id="cyberstorm.user.delete",
        tags=["cyberstorm"],
    )
    def post(self, request, username, format=None):
        if request.user.username != username:
            return Response(
                {"error": "Username doesn't match session user"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = DeleteAccountForm(
            user=request.user,
            data=request.data,
        )
        if form.is_valid():
            # Add tests for this
            request.user.delete()
            return Response(
                {"user": request.user.username},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
