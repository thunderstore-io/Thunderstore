from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageListing
from thunderstore.repository.views.package._utils import get_package_listing_or_404


@transaction.atomic
def update_categories(
    categories: list, user: UserType, listing: PackageListing
) -> None:
    try:
        listing.ensure_update_categories_permission(user)
        listing.update_categories(agent=user, categories=categories)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )


@transaction.atomic
def reject_package_listing(
    reason: str,
    notes: str,
    agent: UserType,
    listing: PackageListing,
) -> None:
    try:
        listing.community.ensure_user_can_moderate_packages(agent)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    listing.reject(agent=agent, rejection_reason=reason, internal_notes=notes)

    listing.clear_review_request()

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )


@transaction.atomic
def approve_package_listing(
    notes: str, agent: UserType, listing: PackageListing
) -> None:
    try:
        listing.community.ensure_user_can_moderate_packages(agent)
    except ValidationError as e:
        raise PermissionValidationError(e.message)

    listing.approve(agent=agent, internal_notes=notes)

    listing.clear_review_request()

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )
