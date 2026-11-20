from typing import Optional

import pytest
from rest_framework.test import APIClient

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import (
    CommunityMemberRole,
    CommunityMembership,
    PackageListing,
)
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.repository.models.team import TeamMemberRole
from thunderstore.repository.tests.utils import create_listing, create_version

TEAM_ROLES = {
    "team_member": TeamMemberRole.member,
    "team_owner": TeamMemberRole.owner,
}
COMMUNITY_ROLES = {
    "community_member": CommunityMemberRole.member,
    "community_janitor": CommunityMemberRole.janitor,
    "community_moderator": CommunityMemberRole.moderator,
    "community_owner": CommunityMemberRole.owner,
}
CAN_MANAGE_LISTING = (
    ("anonymous", False),
    ("team_member", True),
    ("community_moderator", True),
)


def _create_viewer(viewer: str, listing: PackageListing) -> Optional[UserType]:
    if viewer == "anonymous":
        return None
    if viewer == "superuser":
        return UserFactory(is_staff=True, is_superuser=True)

    user = UserFactory()
    if viewer in TEAM_ROLES:
        TeamMemberFactory(
            team=listing.package.owner, user=user, role=TEAM_ROLES[viewer]
        )
    elif viewer in COMMUNITY_ROLES:
        CommunityMembership.objects.create(
            user=user, community=listing.community, role=COMMUNITY_ROLES[viewer]
        )
    elif viewer != "regular_user":
        raise ValueError(f"Unknown viewer: {viewer}")
    return user


def _url(listing: PackageListing, route: str, **params: str) -> str:
    return "/api/cyberstorm/" + route.format(
        community=listing.community.identifier,
        namespace=listing.package.namespace.name,
        package=listing.package.name,
        **params,
    )


# ---------------------------------------------------------------------------
# Listing endpoint: authenticated, so moderators may see rejected versions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(("viewer", "can_manage"), CAN_MANAGE_LISTING)
def test_listing_version__rejected_version_requires_manage_permission(
    api_client: APIClient,
    viewer: str,
    can_manage: bool,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(
        _url(listing, "listing/{community}/{namespace}/{package}/v/2.0.0/")
    )

    assert response.status_code == (200 if can_manage else 404)


@pytest.mark.django_db
def test_listing_version__rejected_version_is_flagged(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("community_moderator", listing))

    response = api_client.get(
        _url(listing, "listing/{community}/{namespace}/{package}/v/2.0.0/")
    )

    assert response.status_code == 200
    assert response.json()["version_is_rejected"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("version", ("1.0.0", "1.5.0"))
def test_listing_version__non_rejected_versions_are_public(
    api_client: APIClient,
    version: str,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "1.5.0", PackageVersionReviewStatus.unreviewed)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)

    response = api_client.get(
        _url(
            listing,
            "listing/{community}/{namespace}/{package}/v/{version}/",
            version=version,
        )
    )

    assert response.status_code == 200
    assert response.json()["full_version_name"].endswith(f"-{version}")
    assert response.json()["version_is_rejected"] is False


@pytest.mark.django_db
@pytest.mark.parametrize(("viewer", "can_manage"), CAN_MANAGE_LISTING)
def test_listing__version_count_includes_rejected_versions_if_user_can_manage_listing(
    api_client: APIClient,
    viewer: str,
    can_manage: bool,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(
        _url(listing, "listing/{community}/{namespace}/{package}/")
    )

    assert response.status_code == 200
    assert response.json()["version_count"] == (2 if can_manage else 1)


@pytest.mark.django_db
@pytest.mark.parametrize(("viewer", "can_manage"), CAN_MANAGE_LISTING)
def test_version_list__rejected_versions_require_manage_permission(
    api_client: APIClient,
    viewer: str,
    can_manage: bool,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(_url(listing, "package/{namespace}/{package}/versions/"))

    expected = {"1.0.0": False, "2.0.0": True} if can_manage else {"1.0.0": False}
    assert response.status_code == 200
    assert "public" not in response.get("Cache-Control", "")
    assert {v["version_number"]: v["is_rejected"] for v in response.json()} == expected


@pytest.mark.django_db
def test_version_list__team_member_sees_rejected_versions_of_unlisted_package(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("team_member", listing))
    url = _url(listing, "package/{namespace}/{package}/versions/")
    listing.delete()

    response = api_client.get(url)

    assert response.status_code == 200
    assert {v["version_number"] for v in response.json()} == {"1.0.0", "2.0.0"}


# ---------------------------------------------------------------------------
# Public (CDN cached, unauthenticated) endpoints: a rejected version must
# never be served, not even to moderators, since the response is cached
# publicly and shared between all users.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    (
        "package/{namespace}/{package}/v/2.0.0/",
        "package/{namespace}/{package}/v/2.0.0/readme/",
        "package/{namespace}/{package}/v/2.0.0/changelog/",
        "package/{namespace}/{package}/v/2.0.0/dependencies/",
    ),
)
@pytest.mark.parametrize("viewer", ("anonymous", "superuser"))
@pytest.mark.parametrize(
    ("review_status", "expected_status"),
    (
        (PackageVersionReviewStatus.approved, 200),
        (PackageVersionReviewStatus.unreviewed, 200),
        (PackageVersionReviewStatus.rejected, 404),
    ),
)
def test_public_version_endpoints__rejected_version_is_hidden(
    api_client: APIClient,
    route: str,
    viewer: str,
    review_status: PackageVersionReviewStatus,
    expected_status: int,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.approved)
    create_version(listing.package, "2.0.0", review_status, changelog="# Changelog")
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(_url(listing, route))

    assert response.status_code == expected_status


# ---------------------------------------------------------------------------
# Packages whose every version is rejected: hidden from the public, but
# moderators must still be able to view and act on them.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    (
        "listing/{community}/{namespace}/{package}/",
        "listing/{community}/{namespace}/{package}/v/1.0.0/",
    ),
)
@pytest.mark.parametrize(("viewer", "can_manage"), CAN_MANAGE_LISTING)
def test_rejected_only_listing__detail_requires_manage_permission(
    api_client: APIClient,
    route: str,
    viewer: str,
    can_manage: bool,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(_url(listing, route))

    assert response.status_code == (200 if can_manage else 404)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    (
        "listing/{community}/{namespace}/{package}/",
        "listing/{community}/{namespace}/{package}/v/1.0.0/",
    ),
)
def test_rejected_only_listing__detail_shows_rejected_version(
    api_client: APIClient,
    route: str,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("community_moderator", listing))

    response = api_client.get(_url(listing, route))

    assert response.status_code == 200
    data = response.json()
    assert data["full_version_name"].endswith("-1.0.0")
    assert data["version_is_rejected"] is True
    assert data["version_count"] == 1
    assert data["latest_version_number"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(("viewer", "can_manage"), CAN_MANAGE_LISTING)
def test_rejected_only_package__version_list_requires_manage_permission(
    api_client: APIClient,
    viewer: str,
    can_manage: bool,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(_url(listing, "package/{namespace}/{package}/versions/"))

    assert response.status_code == (200 if can_manage else 404)


@pytest.mark.django_db
def test_rejected_only_package__version_list_shows_rejected_version(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("community_moderator", listing))

    response = api_client.get(_url(listing, "package/{namespace}/{package}/versions/"))

    assert response.status_code == 200
    assert [v["version_number"] for v in response.json()] == ["1.0.0"]


@pytest.mark.django_db
def test_rejected_only_listing__moderator_can_reject_listing(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("community_moderator", listing))

    response = api_client.post(
        _url(listing, "listing/{community}/{namespace}/{package}/reject/"),
        {"rejection_reason": "Malware"},
        format="json",
    )

    assert response.status_code == 200
    listing.refresh_from_db()
    assert listing.review_status == PackageListingReviewStatus.rejected


@pytest.mark.django_db
def test_rejected_only_listing__team_owner_can_view_status(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("team_owner", listing))

    response = api_client.get(
        _url(listing, "listing/{community}/{namespace}/{package}/status/")
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == listing.review_status


@pytest.mark.django_db
def test_rejected_only_package__team_owner_can_deprecate(
    api_client: APIClient,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer("team_owner", listing))

    response = api_client.post(
        _url(listing, "package/{namespace}/{package}/deprecate/"),
        {"deprecate": True},
        format="json",
    )

    assert response.status_code == 200
    listing.package.refresh_from_db()
    assert listing.package.is_deprecated is True


@pytest.mark.django_db
@pytest.mark.parametrize("viewer", ("community_moderator", "team_owner"))
def test_rejected_only_package__permissions_are_available(
    api_client: APIClient,
    viewer: str,
) -> None:
    listing = create_listing("1.0.0", PackageVersionReviewStatus.rejected)
    api_client.force_authenticate(_create_viewer(viewer, listing))

    response = api_client.get(
        _url(listing, "package/{community}/{namespace}/{package}/permissions/")
    )

    assert response.status_code == 200
