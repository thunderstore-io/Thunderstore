import json

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.cache.cache import BackgroundUpdatedCacheMixin
from thunderstore.core.utils import CommunitySiteSerializerContext
from thunderstore.repository.api.v1.serializers import PackageListingSerializer
from thunderstore.repository.cache import get_package_listing_queryset
from thunderstore.repository.models import Package, PackageRating
from thunderstore.repository.permissions import ensure_can_rate_package


class PackageViewSet(
    BackgroundUpdatedCacheMixin,
    CommunitySiteSerializerContext,
    viewsets.ReadOnlyModelViewSet,
):
    cache_database_fallback = False
    serializer_class = PackageListingSerializer
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
        return get_package_listing_queryset(community_site=self.request.community_site)

    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[SessionAuthentication, BasicAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def rate(self, request, uuid4=None):
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
