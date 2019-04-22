from rest_framework import viewsets

from core.cache import ManualCacheMixin, CacheBustCondition

from repository.api.v1.serializers import (
    PackageSerializer,
)
from repository.cache import get_mod_list_queryset


class PackageViewSet(ManualCacheMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PackageSerializer
    lookup_field = "uuid4"
    cache_until = CacheBustCondition.any_package_version_created

    def get_queryset(self):
        return get_mod_list_queryset()
