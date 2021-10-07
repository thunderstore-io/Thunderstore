import pytest
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from conftest import TestUserTypes
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
    CommunitySite,
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


@pytest.mark.django_db
def test_get_full_url(
    community_site: CommunitySite,
    active_package: Package,
    active_package_listing: PackageListing,
):
    # Just to make sure people test this in the future, if the logic is modified
    community_2 = Community.objects.create(name="Test2", identifier="test2")
    site_2 = Site.objects.create(domain="testsite2.test", name="Testsite2")
    community_site_2 = CommunitySite.objects.create(site=site_2, community=community_2)

    url = active_package_listing.get_full_url()
    comparison_url = str(
        community_site.full_url[:-1] + active_package_listing.get_absolute_url()
    )
    assert url == comparison_url

    active_package_listing_2 = PackageListing.objects.create(
        community=community_2, package=active_package
    )
    url = active_package_listing_2.get_full_url()
    comparison_url = str(
        community_site_2.full_url[:-1] + active_package_listing_2.get_absolute_url()
    )
    assert url == comparison_url

    version_number = active_package_listing.package.versions.first().version_number
    url = active_package_listing.get_full_url(version=version_number)
    comparison_url = str(
        community_site.full_url[:-1]
        + active_package_listing.get_absolute_url()
        + f"{version_number}/"
    )
    assert url == comparison_url


@pytest.mark.django_db
def test_get_package_version_absolute_url(
    active_package_listing: PackageListing,
):
    version_number = active_package_listing.package.versions.first().version_number
    url = active_package_listing.get_package_version_absolute_url(version_number)
    comparison_url = str(
        active_package_listing.get_absolute_url() + f"{version_number}/"
    )
    assert url == comparison_url
