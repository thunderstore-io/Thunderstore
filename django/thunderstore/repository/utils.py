from typing import List, Union

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from thunderstore.cache.cache import CacheBustCondition, cache_function_result
from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.models import Team
from thunderstore.repository.package_reference import PackageReference


def does_contain_package(
    packages: List[PackageReference], package: PackageReference
) -> bool:
    """
    Checks whether or not a list of package references contains a specific
    package, ignoring versions.

    :param packages: A list of PackageReference objects to scan through
    :param package: The package to look for
    :return: True if the package is found, False otherwise
    :rtype: bool
    """
    for reference in packages:
        if reference.without_version == package.without_version:
            return True
    return False


def has_duplicate_packages(packages: List[PackageReference]) -> bool:
    """
    Checks whether or not a list  of package references has duplicates of the
    same package, as opposed to only having unique packages references. Version
    is ignored.

    :param packages: A list of PackageReference objects
    :return: True if duplicate packages are found, False otherwise
    :rtype: bool
    """
    for ref_a in packages:
        for ref_b in packages:
            if ref_a == ref_b:
                continue
            if ref_a.without_version == ref_b.without_version:
                return True
    return False


def unpack_serializer_errors(field, errors, error_dict=None):
    if error_dict is None:
        error_dict = {}

    if isinstance(errors, list) and len(errors) == 1:
        errors = errors[0]

    if isinstance(errors, dict):
        for key, value in errors.items():
            error_dict = unpack_serializer_errors(f"{field} {key}", value, error_dict)
    elif isinstance(errors, list):
        for index, entry in enumerate(errors):
            error_dict = unpack_serializer_errors(f"{field} {index}", entry, error_dict)
    else:
        error_dict[field] = str(errors)
    return error_dict


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_listing(
    owner: Union[Team, str, None] = None,
    name: Union[str, None] = None,
    community: Union[Community, None] = None,
) -> PackageListing:
    filters = Q()
    if owner:
        team_name = owner.name if isinstance(owner, Team) else owner
        filters.add(Q(package__owner__name=team_name), Q.AND)
    if name:
        filters.add(Q(package__name=name), Q.AND)
    if community:
        filters.add(Q(community=community), Q.AND)
    package_listing = (
        PackageListing.objects.active()
        .filter(filters)
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


def solve_listing(
    owner: Union[Team, str, None] = None,
    name: Union[str, None] = None,
    community: Union[Community, None] = None,
):
    try:
        if community is None:
            raise ValueError("Community is None, skip trying to fetch with it")
        listing = get_listing(
            owner=owner,
            name=name,
            community=community,
        )
    except (Http404, ValueError):  # Try to find in another community
        listing = get_listing(
            owner=owner,
            name=name,
        )
    return listing
