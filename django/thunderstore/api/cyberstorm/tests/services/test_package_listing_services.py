import pytest
from thunderstore.core.exceptions import PermissionValidationError

from thunderstore.api.cyberstorm.services.package_listing import (
    approve_package_listing,
    reject_package_listing,
    update_categories,
)
from thunderstore.community.consts import PackageListingReviewStatus

from conftest import TestUserTypes


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_moderate",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, False),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_update_categories(
    user, active_package_listing, package_category, user_role, can_moderate
):

    categories = [package_category]
    user = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            update_categories(
                categories=categories, user=user, listing=active_package_listing
            )
    else:
        update_categories(
            categories=categories, user=user, listing=active_package_listing
        )
        active_package_listing.refresh_from_db()
        assert active_package_listing.categories.count() == 1
        assert package_category in active_package_listing.categories.all()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_reject",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, False),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_reject_package_listing(active_package_listing, user_role, can_reject):
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_reject:
        with pytest.raises(PermissionValidationError):
            reject_package_listing(
                reason="Inappropriate content",
                notes="This package contains inappropriate content.",
                agent=agent,
                listing=active_package_listing,
            )
    else:
        reject_package_listing(
            reason="Inappropriate content",
            notes="This package contains inappropriate content.",
            agent=agent,
            listing=active_package_listing,
        )
        active_package_listing.refresh_from_db()
        assert active_package_listing.is_rejected is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_approve",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, False),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_approve_package_listing(active_package_listing, user_role, can_approve):
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_approve:
        with pytest.raises(PermissionValidationError):
            approve_package_listing(
                notes="This package is approved.",
                agent=agent,
                listing=active_package_listing,
            )
    else:
        approve_package_listing(
            notes="This package is approved.",
            agent=agent,
            listing=active_package_listing,
        )
        active_package_listing.refresh_from_db()
        assert active_package_listing.review_status == (
            PackageListingReviewStatus.approved
        )


@pytest.mark.django_db
def test_approve_package_listing_no_community_membership(active_package_listing, user):
    with pytest.raises(PermissionValidationError):
        approve_package_listing(
            notes="This package is approved.",
            agent=user,
            listing=active_package_listing,
        )


@pytest.mark.django_db
def test_update_categories_no_community_membership(
    user, active_package_listing, package_category
):
    categories = [package_category]

    with pytest.raises(PermissionValidationError):
        update_categories(
            categories=categories, user=user, listing=active_package_listing
        )


@pytest.mark.django_db
def test_reject_package_listing_no_community_membership(active_package_listing, user):
    with pytest.raises(PermissionValidationError):
        reject_package_listing(
            reason="Inappropriate content",
            notes="This package contains inappropriate content.",
            agent=user,
            listing=active_package_listing,
        )
