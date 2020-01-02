from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.cache import ManualCacheMixin, CacheBustCondition

from repository.api.v1.serializers import (
    PackageSerializer,
)
from repository.models import PackageRating
from repository.cache import get_mod_list_queryset


class PackageViewSet(ManualCacheMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PackageSerializer
    lookup_field = "uuid4"
    cache_until = CacheBustCondition.any_package_updated

    def get_queryset(self):
        return get_mod_list_queryset()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, uuid4=None):
        package = self.get_object()
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Must be logged in")
        target_state = request.data.get("target_state")
        result_state = ""
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
