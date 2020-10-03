import json

from django.http import HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework.schemas import AutoSchema

from thunderstore.core.cache import CacheBustCondition, cache_function_result, BackgroundUpdatedCacheMixin
from thunderstore.repository.models import Package

from thunderstore.repository.api.experimental.serializers import PackageSerializerExperimental


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
    schema = PackageListSchema()

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse(
            json.dumps({"error": "No cache available"}),
            status=503,
            content_type="application/json"
        )

    def get_queryset(self):
        return get_mod_list_queryset()
