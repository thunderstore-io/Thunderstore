from thunderstore.repository.models import Package

from thunderstore.core.cache import (
    CacheBustCondition,
    cache_function_result
)


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
            "versions",
            "versions__dependencies",
            "package_listings",
        )
        .order_by("-is_pinned", "is_deprecated", "-date_updated")
    )
