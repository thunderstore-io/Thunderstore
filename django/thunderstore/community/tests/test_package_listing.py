import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from conftest import TestUserTypes
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
    PackageListing,
    PackageListingReviewStatus,
)
from thunderstore.repository.models import Package, TeamMember, TeamMemberRole


@pytest.mark.django_db
def test_package_listing_only_one_per_community(
    active_package: Package, community: Community
) -> None:
    l1 = PackageListing.objects.create(package=active_package, community=community)
    assert l1.pk
    with pytest.raises(IntegrityError) as exc:
        PackageListing.objects.create(package=active_package, community=community)
    assert "one_listing_per_community" in str(exc.value)


@pytest.mark.django_db
def test_package_listing_community_read_only(
    active_package_listing: PackageListing,
) -> None:
    c = Community.objects.create(name="Test Community")
    with pytest.raises(ValidationError) as exc:
        active_package_listing.community = c
        active_package_listing.save()
    assert "PackageListing.community is read only" in str(exc.value)


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
def test_package_listing_is_waiting_for_approval(
    active_package_listing: PackageListing,
    require_approval: bool,
    review_status: str,
) -> None:
    active_package_listing.review_status = review_status
    active_package_listing.save()
    community = active_package_listing.community
    community.require_package_listing_approval = require_approval
    community.save()
    if require_approval:
        assert active_package_listing.is_waiting_for_approval == (
            review_status != PackageListingReviewStatus.approved
        )
    else:
        assert active_package_listing.is_waiting_for_approval is False


@pytest.mark.django_db
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
def test_package_listing_is_waiting_for_approval(
    active_package_listing: PackageListing,
    review_status: str,
) -> None:
    active_package_listing.review_status = review_status
    active_package_listing.save()
    assert active_package_listing.is_rejected is (
        review_status == PackageListingReviewStatus.rejected
    )


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("team_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("community_role", CommunityMemberRole.options() + [None])
def test_package_listing_ensure_can_be_viewed_by_user(
    active_package_listing: PackageListing,
    require_approval: bool,
    review_status: str,
    user_type: str,
    community_role: str,
    team_role: str,
):
    listing = active_package_listing
    listing.review_status = review_status
    listing.save()

    community = listing.community
    community.require_package_listing_approval = require_approval
    community.save()
    user = TestUserTypes.get_user_by_type(user_type)
    if community_role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=community,
            role=community_role,
        )
    if team_role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(
            user=user,
            team=listing.package.owner,
            role=team_role,
        )

    result = listing.can_be_viewed_by_user(user)
    error = None
    expected_error = "Insufficient permissions to view"
    try:
        listing.ensure_can_be_viewed_by_user(user)
    except ValidationError as e:
        error = str(e)

    if require_approval:
        if review_status == PackageListingReviewStatus.approved:
            assert result is True
            assert error is None
        elif user is None:
            assert result is False
            assert expected_error in error
        elif not user.is_authenticated:
            assert result is False
            assert expected_error in error
        elif community.can_user_manage_packages(user):
            assert result is True
            assert error is None
        elif listing.package.owner.can_user_access(user):
            assert result is True
            assert error is None
    else:
        if review_status != PackageListingReviewStatus.rejected:
            assert result is True
            assert error is None
        elif user is None:
            assert result is False
            assert expected_error in error
        elif not user.is_authenticated:
            assert result is False
            assert expected_error in error
        elif community.can_user_manage_packages(user):
            assert result is True
            assert error is None
        elif listing.package.owner.can_user_access(user):
            assert result is True
            assert error is None
