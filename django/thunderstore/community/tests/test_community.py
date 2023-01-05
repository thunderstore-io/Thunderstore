import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, CommunitySiteFactory
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
)
from thunderstore.community.models.community import get_community_filepath
from thunderstore.community.models.community_site import CommunitySite


@pytest.mark.django_db
def test_community_manager_listed():
    c1 = CommunityFactory(is_listed=True)
    c2 = CommunityFactory(is_listed=False)

    listed_communities = Community.objects.listed()
    assert c1 in listed_communities
    assert c2 not in listed_communities


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", CommunityMemberRole.options() + [None])
def test_community_ensure_user_can_manage_packages(
    community: Community,
    user_type: str,
    role: str,
):
    user = TestUserTypes.get_user_by_type(user_type)
    if role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=community,
            role=role,
        )

    result = community.can_user_manage_packages(user)
    error = None
    try:
        community.ensure_user_can_manage_packages(user)
    except ValidationError as e:
        error = str(e)

    if user_type in TestUserTypes.fake_users():
        assert result is False
        assert "Must be authenticated" in error
        return
    elif user_type == TestUserTypes.deactivated_user:
        assert result is False
        assert "User has been deactivated" in error
    elif user_type == TestUserTypes.service_account:
        assert result is False
        assert "Service accounts are unable to manage packages" in error
    elif role not in (
        CommunityMemberRole.moderator,
        CommunityMemberRole.owner,
    ) and not (user.is_superuser or user.is_staff):
        assert result is False
        assert "Must be a moderator or higher to manage packages" in error
    else:
        assert result is True
        assert error is None


@pytest.mark.django_db
def test_background_image_url_when_community_has_no_image():
    community = CommunityFactory()
    url = community.background_image_url
    assert url is None


@pytest.mark.django_db
def test_background_image_url_when_community_has_image(dummy_image):
    community = CommunityFactory(background_image=dummy_image)
    url = community.background_image_url
    assert isinstance(url, str)
    assert len(url) > 0


@pytest.mark.django_db
def test_community_site_get_absolute_url(community_site: CommunitySite) -> None:
    assert community_site.get_absolute_url == "/c/test/"


@pytest.mark.django_db
def test_community_get_community_filepath(community: Community) -> None:
    assert (
        get_community_filepath(community, "lol.png")
        == f"community/{community.identifier}/lol.png"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
def test_community_valid_review_statuses(
    community: Community, require_approval: bool
) -> None:
    community.require_package_listing_approval = require_approval
    community.save()
    if require_approval:
        assert community.valid_review_statuses == (PackageListingReviewStatus.approved,)
    else:
        assert community.valid_review_statuses == (
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.unreviewed,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
def test_community_site_url(
    community: Community,
    has_site: bool,
) -> None:
    if has_site:
        site = CommunitySiteFactory(community=community)
        expected = site.full_url
    else:
        expected = f"/c/{community.identifier}/"
    assert community.site_url == expected
