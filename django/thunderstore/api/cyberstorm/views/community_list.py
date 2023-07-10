from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.community.models import Community


class CommunityPaginator(PageNumberPagination):
    page_size = 100


class CommunityListAPIView(ListAPIView):
    permission_classes = []
    serializer_class = CyberstormCommunitySerializer
    pagination_class = CommunityPaginator
    queryset = Community.objects.listed()
    filter_backends = [StrictOrderingFilter]
    ordering_fields = ["identifier"]
    ordering = ["identifier"]
