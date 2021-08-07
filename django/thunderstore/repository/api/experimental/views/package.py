from django.db.models import Count, QuerySet, Sum
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.pagination import CursorPagination

from thunderstore.cache.cache import CacheBustCondition, ManualCacheMixin
from thunderstore.repository.api.experimental.serializers import (
    PackageSerializerExperimental,
)
from thunderstore.repository.models import Package
from thunderstore.repository.package_reference import PackageReference


def get_package_queryset() -> "QuerySet[Package]":
    return (
        Package.objects.active()
        .select_related(
            "owner",
            "latest",
            "latest__package",
            "latest__package__owner",
        )
        .prefetch_related(
            "latest__dependencies",
            "latest__dependencies__package",
            "latest__dependencies__package__owner",
            "community_listings",
            "community_listings__categories",
            "community_listings__community",
        )
        .annotate(
            _total_downloads=Sum("versions__downloads"),
        )
        .annotate(
            _rating_score=Count("package_ratings"),
        )
    )


class CustomCursorPagination(CursorPagination):
    ordering = "-date_created"
    page_size = 5


class PackageListApiView(ManualCacheMixin, ListAPIView):
    """
    Lists all available packages
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializerExperimental
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return get_package_queryset()


class PackageDetailApiView(ManualCacheMixin, RetrieveAPIView):
    """
    Get a single package
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializerExperimental

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            reference = PackageReference(
                namespace=self.kwargs["namespace"],
                name=self.kwargs["name"],
            )
        except ValueError as e:
            raise ValidationError(str(e))
        obj = get_object_or_404(queryset, **reference.get_filter_kwargs())
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        return get_package_queryset()

    @swagger_auto_schema(operation_id="experimental_package_read")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
