from rest_framework import viewsets

from repository.api.v1.serializers import (
    PackageSerializer,
)
from repository.cache import get_mod_list_queryset


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PackageSerializer
    lookup_field = "uuid4"

    def get_queryset(self):
        return get_mod_list_queryset()
