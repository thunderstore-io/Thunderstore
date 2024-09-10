from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.models import Community


class CommunityPaginator(PageNumberPagination):
    page_size = 150


class CommunityListAPIView(CyberstormAutoSchemaMixin, ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CyberstormCommunitySerializer
    pagination_class = CommunityPaginator
    queryset = Community.objects.listed()
    filter_backends = [SearchFilter, StrictOrderingFilter]
    search_fields = ["name"]
    ordering_fields = [
        "aggregated_fields__download_count",
        "aggregated_fields__package_count",
        "datetime_created",
        "identifier",
        "name",
    ]
    ordering = ["identifier"]
