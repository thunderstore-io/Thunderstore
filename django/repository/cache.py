from repository.models import Package

from core.cache import (
    CacheBustCondition,
    cache_function_result
)


@cache_function_result(cache_until=CacheBustCondition.any_package_version_created)
def get_mod_list_queryset():
    return (
        Package.objects
        .filter(is_active=True)
        .prefetch_related("versions")
        .order_by("-is_pinned", "-date_updated")
    )
