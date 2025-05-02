from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageRating


@transaction.atomic
def deprecate_package(agent: UserType, package: Package) -> Package:
    try:
        package.ensure_user_can_manage_deprecation(agent)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    package.deprecate()
    return package


@transaction.atomic
def undeprecate_package(agent: UserType, package: Package) -> Package:
    try:
        package.ensure_user_can_manage_deprecation(agent)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    package.undeprecate()
    return package


@transaction.atomic
def rate_package(agent: UserType, package: Package, target_state: str):
    result_state = PackageRating.rate_package(
        agent=agent,
        package=package,
        target_state=target_state,
    )

    package = Package.objects.get(id=package.id)
    return package.rating_score, result_state
