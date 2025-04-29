from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageRating


@transaction.atomic
def deprecate_package(package: Package, user: UserType) -> Package:
    try:
        package.ensure_user_can_manage_deprecation(user)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    package.deprecate()
    return package


@transaction.atomic
def undeprecate_package(package: Package, user: UserType) -> Package:
    try:
        package.ensure_user_can_manage_deprecation(user)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    package.undeprecate()
    return package


@transaction.atomic
def rate_package(package: Package, agent: UserType, target_state: str):
    result_state = PackageRating.rate_package(
        agent=agent,
        package=package,
        target_state=target_state,
    )

    package = Package.objects.get(id=package.id)
    return package.rating_score, result_state
