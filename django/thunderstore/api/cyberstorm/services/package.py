from typing import Literal, Tuple, Union

from django.db import transaction

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageRating


@transaction.atomic
def deprecate_package(agent: UserType, package: Package) -> Package:
    package.ensure_user_can_manage_deprecation(agent)
    package.deprecate()
    return package


@transaction.atomic
def undeprecate_package(agent: UserType, package: Package) -> Package:
    package.ensure_user_can_manage_deprecation(agent)
    package.undeprecate()
    return package


RATING_STATE = Union[Literal["rated"], Literal["unrated"]]


@transaction.atomic
def rate_package(
    agent: UserType, package: Package, target_state: RATING_STATE
) -> Tuple[int, RATING_STATE]:
    result_state = PackageRating.rate_package(
        agent=agent,
        package=package,
        target_state=target_state,
    )

    package = Package.objects.get(id=package.id)
    return package.rating_score, result_state
