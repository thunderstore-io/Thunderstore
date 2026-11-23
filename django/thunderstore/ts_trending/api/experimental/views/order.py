from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import PublicCacheMixin
from thunderstore.community.models import Community
from thunderstore.ts_trending.api.experimental.serializers import (
    OrderResponseSerializer,
)
from thunderstore.ts_trending.services.score import get_package_order


class TrendingOrderApiView(PublicCacheMixin, APIView):
    """
    List a community's full package names in trending order.
    """

    cache_max_age = 60 * 5

    @swagger_auto_schema(
        operation_id="experimental.trending.order",
        responses={200: OrderResponseSerializer()},
        tags=["experimental"],
    )
    def get(self, request: Request, community_id: str) -> HttpResponse:
        community = get_object_or_404(Community, identifier=community_id)
        order = get_package_order(community)
        return Response(OrderResponseSerializer(order).data)
