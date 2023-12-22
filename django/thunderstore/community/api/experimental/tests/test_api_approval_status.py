import json

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
from thunderstore.repository.models import TeamMember


@pytest.fixture(params=[CommunityMemberRole.moderator, CommunityMemberRole.owner])
def moderator(request, active_package_listing: PackageListing):
    user = UserFactory()
    CommunityMembership.objects.create(
        user=user,
        role=request.param,
        community=active_package_listing.community,
    )
    return user


@pytest.mark.django_db
def test_api_experimental_package_listing_approve_success(
    api_client: APIClient,
    active_package_listing: PackageListing,
    moderator: UserType,
):
    api_client.force_authenticate(user=moderator)
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/approve/",
        content_type="application/json",
    )

    assert response.status_code == 200
    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.approved


@pytest.mark.django_db
def test_api_experimental_package_listing_approve_fail(
    api_client: APIClient,
    active_package_listing: PackageListing,
    team_owner: TeamMember,
):
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/approve/",
        content_type="application/json",
    )
    assert response.status_code == 403

    api_client.force_authenticate(user=team_owner.user)
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/approve/",
        content_type="application/json",
    )
    assert response.status_code == 403

    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.unreviewed


@pytest.mark.django_db
def test_api_experimental_package_listing_reject_success(
    api_client: APIClient,
    active_package_listing: PackageListing,
    moderator: UserType,
):
    reason = "Bad upload"
    api_client.force_authenticate(user=moderator)
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/reject/",
        data=json.dumps({"rejection_reason": reason}),
        content_type="application/json",
    )

    assert response.status_code == 200
    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.rejected
    assert active_package_listing.rejection_reason == reason


@pytest.mark.django_db
def test_api_experimental_package_listing_reject_fail(
    api_client: APIClient,
    active_package_listing: PackageListing,
    team_owner: TeamMember,
):
    reason = "Bad upload"
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/reject/",
        data=json.dumps({"rejection_reason": reason}),
        content_type="application/json",
    )
    assert response.status_code == 403

    api_client.force_authenticate(user=team_owner.user)
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/reject/",
        data=json.dumps({"rejection_reason": reason}),
        content_type="application/json",
    )
    assert response.status_code == 403

    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.unreviewed
