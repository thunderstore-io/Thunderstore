from typing import List

from repository.package_reference import PackageReference


def does_contain_package(packages: List[PackageReference], package: PackageReference) -> bool:
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
