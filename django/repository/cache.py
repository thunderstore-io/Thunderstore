from core.cache import cache_function_result

from repository.models import Package


@cache_function_result(cache_key="modlist-all")
def get_mod_list_queryset():
    return (
        Package.objects
        .filter(is_active=True)
        .prefetch_related("versions")
        .order_by("-is_pinned", "-date_updated")
    )
