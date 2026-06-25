from typing import Optional

from django.db import transaction

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.models import Package, PackageListing, PackageVersion
from thunderstore.repository.views.package._utils import get_package_listing_or_404
from thunderstore.ts_reports.models import PackageReport


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


@transaction.atomic
def set_package_listing_unreviewed(
    agent: UserType, listing: PackageListing, notes: Optional[str] = None
) -> None:
    from thunderstore.community.consts import PackageListingReviewStatus

    listing.community.ensure_user_can_moderate_packages(agent)

    update_fields = ["review_status"]
    listing.review_status = PackageListingReviewStatus.unreviewed
    # Let the moderator jot/keep internal notes without committing to a decision.
    if notes is not None and notes != listing.notes:
        listing.notes = notes
        update_fields.append("notes")
    listing.save(update_fields=tuple(update_fields))

    # Review status feeds visibility checks (PackageListingViewMixin.get_object),
    # so the cached listing lookup must be busted like it is for approve/reject.
    get_package_listing_or_404.clear_cache_with_args(
        namespace=listing.package.namespace.name,
        name=listing.package.name,
        community=listing.community,
    )


@transaction.atomic
def report_package_listing(
    agent: UserType,
    reason: str,
    package: Package,
    package_listing: PackageListing,
    package_version: PackageVersion,
    description: str,
) -> None:
    user = validate_user(agent)

    PackageReport.handle_user_report(
        reason=reason,
        submitted_by=user,
        package=package,
        package_listing=package_listing,
        package_version=package_version,
        description=description,
    )


@transaction.atomic
def unlist_package_listing(agent: UserType, listing: PackageListing) -> None:

    user = validate_user(agent)
    if not user.is_superuser:
        raise PermissionValidationError("Only superusers can unlist packages")

    listing.package.deactivate()
