from rest_framework import serializers
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    CyberstormTimedCacheMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.community.models import Community


class CommunityPaginator(PageNumberPagination):
    page_size = 300


class CommunityListAPIQueryParams(serializers.Serializer):
    include_unlisted = serializers.BooleanField(default=False)


class CommunityListAPIView(CyberstormTimedCacheMixin, CyberstormAutoSchemaMixin, ListAPIView):
    permission_classes = []
    serializer_class = CyberstormCommunitySerializer
    pagination_class = CommunityPaginator
    filter_backends = [SearchFilter, StrictOrderingFilter]
    search_fields = ["name", "search_keywords"]
    ordering_fields = [
        "aggregated_fields__download_count",
        "aggregated_fields__package_count",
        "datetime_created",
        "identifier",
        "name",
    ]
    ordering = ["identifier"]

    def get_queryset(self):
        query_params = CommunityListAPIQueryParams(data=self.request.query_params)
        query_params.is_valid(raise_exception=True)

        if query_params.validated_data["include_unlisted"]:
            return Community.objects.all()
        else:
            return Community.objects.listed()

    @conditional_swagger_auto_schema(
        tags=["cyberstorm"],
        query_serializer=CommunityListAPIQueryParams(),
    )
    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        return response
