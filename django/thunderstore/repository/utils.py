from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from thunderstore.repository.package_reference import PackageReference


def does_contain_package(
    packages: List["PackageReference"], package: "PackageReference"
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


def has_duplicate_packages(packages: List["PackageReference"]) -> bool:
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


def has_expired(
    timestamp: Optional[datetime],
    now: datetime,
    ttl_seconds: float,
) -> bool:
    if timestamp is None:
        return True
    return (now - timestamp).total_seconds() > ttl_seconds
