from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.schemas import AutoSchema

from core.cache import CacheBustCondition, cache_function_result, BackgroundUpdatedCacheMixin
from repository.models import Package

from repository.api.experimental.serializers import PackageSerializerExperimental


class PackagePaginator(PageNumberPagination):
    page_size = 30
    page_size_query_param = None


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_mod_list_queryset():
    return (
        Package.objects
        .active()
        .select_related(
            "owner",
            "latest",
        )
        .prefetch_related(
            "latest__dependencies",
        )
        .order_by("-is_pinned", "is_deprecated", "-date_updated")
    )


class PackageListSchema(AutoSchema):
    pass


class PackageListApiView(BackgroundUpdatedCacheMixin, ListAPIView):
    """
    Lists all available packages
    """
    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializerExperimental
    pagination_class = PackagePaginator
    schema = PackageListSchema()

    def get_queryset(self):
        return get_mod_list_queryset()
