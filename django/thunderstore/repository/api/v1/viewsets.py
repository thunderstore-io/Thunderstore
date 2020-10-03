import json

from django.http import HttpResponse

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.core.cache import BackgroundUpdatedCacheMixin

from thunderstore.repository.api.v1.serializers import (
    PackageSerializer,
)
from thunderstore.repository.models import PackageRating
from thunderstore.repository.cache import get_mod_list_queryset


class PackageViewSet(BackgroundUpdatedCacheMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PackageSerializer
    lookup_field = "uuid4"

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse(
            json.dumps({"error": "No cache available"}),
            status=503,
            content_type="application/json"
        )

    def get_queryset(self):
        return get_mod_list_queryset()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, uuid4=None):
        package = self.get_object()
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Must be logged in")
        target_state = request.data.get("target_state")
        if target_state == "rated":
            PackageRating.objects.get_or_create(rater=user, package=package)
            result_state = "rated"
        else:
            PackageRating.objects.filter(rater=user, package=package).delete()
            result_state = "unrated"
        return Response({
            "state": result_state,
            "score": package.rating_score,
        })
