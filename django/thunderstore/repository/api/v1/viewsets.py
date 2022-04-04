import json
from typing import Any

from django.http import HttpResponse
from django.utils.cache import get_conditional_response
from django.utils.http import http_date
from rest_framework import viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from thunderstore.community.models import CommunitySite
from thunderstore.core.types import HttpRequestType
from thunderstore.core.utils import CommunitySiteSerializerContext
from thunderstore.repository.api.v1.serializers import PackageListingSerializer
from thunderstore.repository.cache import get_package_listing_queryset
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import Package, PackageRating
from thunderstore.repository.models.cache import APIV1PackageCache
from thunderstore.repository.permissions import ensure_can_rate_package

PACKAGE_SERIALIZER = PackageListingSerializer


def serialize_package_list_for_community(community_site: CommunitySite) -> bytes:
    queryset = get_package_listing_queryset(
        community_identifier=community_site.community.identifier
    )
    serializer = PACKAGE_SERIALIZER(
        queryset,
        many=True,
        context={
            "community_site": community_site,
        },
    )
    return JSONRenderer().render(serializer.data)


class PackageViewSet(
    CommunityMixin,
    CommunitySiteSerializerContext,
    viewsets.ReadOnlyModelViewSet,
):
    cache_database_fallback = False
    serializer_class = PACKAGE_SERIALIZER
    lookup_field = "package__uuid4"
    lookup_url_kwarg = "uuid4"

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse(
            json.dumps({"error": "No cache available"}),
            status=503,
            content_type="application/json",
        )

    def get_queryset(self):
        if self.community_identifier:
            return get_package_listing_queryset(
                community_identifier=self.community_identifier
            )
        return get_package_listing_queryset(
            community_identifier=self.request.community.identifier
        )

    def list(self, request: HttpRequestType, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.community_identifier:
            cache = APIV1PackageCache.get_latest_for_community(
                community_identifier=self.community_identifier
            )
        else:
            cache = APIV1PackageCache.get_latest_for_community(
                community=request.community
            )
        if not cache or not cache.data:
            return self.get_no_cache_response()
        last_modified = int(cache.last_modified.timestamp())

        # TODO: Add ETag support if useful
        # Check if we can return a 304 response, otherwise return full content
        response = get_conditional_response(request, last_modified=last_modified)
        if response is None:
            # TODO: Stream directly from the S3 backend instead of buffering
            # TODO: Should we support decompressing for non-gzip capable clients?
            response = HttpResponse(
                content=cache.data,
                content_type=cache.content_type,
            )
            response["Last-Modified"] = http_date(last_modified)
            response["Content-Encoding"] = cache.content_encoding

        return response

    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[SessionAuthentication, BasicAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def rate(self, request, uuid4=None, community_identifier=None):
        package = get_object_or_404(Package.objects.active(), uuid4=uuid4)
        user = request.user
        ensure_can_rate_package(user, package)
        target_state = request.data.get("target_state")
        if target_state == "rated":
            PackageRating.objects.get_or_create(rater=user, package=package)
            result_state = "rated"
        else:
            PackageRating.objects.filter(rater=user, package=package).delete()
            result_state = "unrated"
        return Response(
            {
                "state": result_state,
                "score": package.rating_score,
            },
        )
