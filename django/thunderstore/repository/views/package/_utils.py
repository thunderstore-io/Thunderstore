from typing import List, Optional

from django.http import Http404
from django.shortcuts import get_object_or_404

from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
    PackageListing,
)
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


def get_moderated_communities(user: Optional[UserType]) -> List[str]:
    if not user or not user.is_authenticated:
        return []

    is_global_moderator = user.is_superuser or (
        user.is_staff and user.has_perm("community.change_packagelisting")
    )
    if is_global_moderator:
        return [
            str(x)
            for x in Community.objects.order_by("pk").values_list("pk", flat=True)
        ]
    else:
        return [
            str(x)
            for x in CommunityMembership.objects.filter(
                user=user,
                role__in=(
                    CommunityMemberRole.owner,
                    CommunityMemberRole.moderator,
                ),
            )
            .order_by("pk")
            .values_list("community_id", flat=True)
        ]
