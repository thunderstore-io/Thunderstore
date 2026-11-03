from rest_framework import serializers
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    PublicCacheMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.community.models import Community


class CommunityPaginator(PageNumberPagination):
    def paginate_queryset(self, queryset, request, view=None):
        return list(queryset)

    def get_paginated_response(self, data):
        # We return all communities on a single page to remove the
        # need to hardcode a community limit per page (used to be 500).
        # A bit of a hack, since we're spoofing the shape of the paginated
        # output data, but it's easier to do it like this.
        return Response(
            {
                "count": len(data),
                "next": None,
                "previous": None,
                "results": data,
            }
        )


class CommunityListAPIQueryParams(serializers.Serializer):
    include_unlisted = serializers.BooleanField(default=False)


class CommunityListAPIView(PublicCacheMixin, CyberstormAutoSchemaMixin, ListAPIView):
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
