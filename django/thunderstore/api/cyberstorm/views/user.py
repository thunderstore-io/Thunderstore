from django.contrib.auth import get_user_model
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import CyberstormUserSerializer

User = get_user_model()

class UserAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CyberstormUserSerializer()},
        operation_id="api.user",
    )
    def get(self, request: HttpRequest, user_identifier: str) -> HttpResponse:
        try:
            u = User.objects.get(
                username=user_identifier,
            )
        except User.DoesNotExist:
            raise Http404(f"Coudln't find user with the identifier {user_identifier}")
        
        serializer = self.serialize_results(u)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def serialize_results(self, user: User):
        return CyberstormUserSerializer(
            {
                "name": user.username,
                "accountCreated": user.date_joined,
                "lastActive": user.last_login,
            }
        )