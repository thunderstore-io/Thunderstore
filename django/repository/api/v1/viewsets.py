from rest_framework import viewsets

from repository.models import Package
from repository.api.v1.serializers import (
    PackageSerializer,
)


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.filter(is_active=True)
    serializer_class = PackageSerializer
