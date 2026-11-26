from typing import Any, Optional

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion


def create_listing(
    version_number: str,
    review_status: PackageVersionReviewStatus,
    community: Optional[Community] = None,
    is_active: bool = True,
    listing_review_status: PackageListingReviewStatus = (
        PackageListingReviewStatus.unreviewed
    ),
    **version_kwargs: Any,
) -> PackageListing:
    """
    Create a listing whose package has a single version in the given state.
    """
    return PackageListingFactory(
        community_=community,
        review_status=listing_review_status,
        package_version_kwargs={
            "version_number": version_number,
            "review_status": review_status,
            "is_active": is_active,
            **version_kwargs,
        },
    )


def create_version(
    package: Package,
    version_number: str,
    review_status: PackageVersionReviewStatus,
    is_active: bool = True,
    **version_kwargs: Any,
) -> PackageVersion:
    return PackageVersionFactory(
        package=package,
        name=package.name,
        version_number=version_number,
        review_status=review_status,
        is_active=is_active,
        **version_kwargs,
    )
