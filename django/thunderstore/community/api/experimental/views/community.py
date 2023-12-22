from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.api.experimental.views._utils import (
    CustomCursorPagination,
    CustomListAPIView,
)
from thunderstore.community.models import Community
from thunderstore.frontend.api.experimental.serializers.views import CommunitySerializer


class CommunitiesExperimentalApiView(CustomListAPIView):
    pagination_class = CustomCursorPagination
    queryset = Community.objects.listed()
    serializer_class = CommunitySerializer

    @swagger_auto_schema(tags=["experimental"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class CurrentCommunityExperimentalApiView(APIView):
    serializer_class = CommunitySerializer

    @swagger_auto_schema(
        responses={200: serializer_class()},
        operation_id="experimental.community.current",
        operation_description="Fetch the Community of the queried domain",
        tags=["experimental"],
    )
    def get(self, request, *args, **kwargs):
        serializer = CommunitySerializer(request.community)
        return Response(serializer.data, status=status.HTTP_200_OK)
