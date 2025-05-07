from django.db import transaction

from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageListing
from thunderstore.repository.views.package._utils import get_package_listing_or_404


@transaction.atomic
def update_categories(
    agent: UserType, categories: list, listing: PackageListing
) -> None:
    listing.ensure_update_categories_permission(agent)
    listing.update_categories(agent=agent, categories=categories)

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )


@transaction.atomic
def reject_package_listing(
    agent: UserType,
    reason: str,
    notes: str,
    listing: PackageListing,
) -> None:
    listing.community.ensure_user_can_moderate_packages(agent)

    listing.reject(agent=agent, rejection_reason=reason, internal_notes=notes)
    listing.clear_review_request()

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )


@transaction.atomic
def approve_package_listing(
    agent: UserType, notes: str, listing: PackageListing
) -> None:
    listing.community.ensure_user_can_moderate_packages(agent)

    listing.approve(agent=agent, internal_notes=notes)
    listing.clear_review_request()

    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )
