from django.http import Http404
from django.shortcuts import get_object_or_404

from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.community.models import Community, PackageListing
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, Team


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_package_listing_or_404(
    namespace: str,
    name: str,
    community: Community,
) -> PackageListing:
    owner = get_object_or_404(Team, name=namespace)
    package_listing = (
        PackageListing.objects.active()
        .filter(
            package__owner=owner,
            package__name=name,
            community=community,
        )
        .select_related(
            "package",
            "package__owner",
            "package__latest",
        )
        .prefetch_related(
            "categories",
        )
        .first()
    )
    if not package_listing:
        raise Http404("No matching package found")
    return package_listing


def can_view_listing_admin(user: UserType, obj: PackageListing):
    # TODO: Object level permissions once implemented
    return user.is_staff and user.has_perm("community.view_packagelisting")


def can_view_package_admin(user: UserType, obj: Package):
    # TODO: Object level permissions once implemented
    return user.is_staff and user.has_perm("repository.view_package")
