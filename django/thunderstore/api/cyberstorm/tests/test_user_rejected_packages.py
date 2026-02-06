import pytest
from rest_framework.test import APIClient

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import PackageListingFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import (
    PackageFactory,
    TeamFactory,
    TeamMemberFactory,
)


def get_user_rejected_listings_url() -> str:
    return "/api/cyberstorm/user/rejected-package-listings/"


@pytest.mark.django_db
def test_user_rejected_package_listings__requires_authentication(api_client: APIClient):
    response = api_client.get(get_user_rejected_listings_url())

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_user_rejected_package_listings__returns_only_users_team_rejected(
    api_client: APIClient, user: UserType
) -> None:
    # Create a team and add the user as a member/owner
    membership = TeamMemberFactory(user=user, role="owner")
    team = membership.team

    # Rejected listings owned by the user's team (should be returned)
    expected1 = PackageListingFactory(
        review_status=PackageListingReviewStatus.rejected,
        package_kwargs=dict(owner=team),
    )
    expected2 = PackageListingFactory(
        review_status=PackageListingReviewStatus.rejected,
        package_kwargs=dict(owner=team),
    )

    # Non-rejected listing for the same team (should be filtered out)
    PackageListingFactory(
        review_status=PackageListingReviewStatus.approved,
        package_kwargs=dict(owner=team),
    )

    # Rejected listing for another team (should be filtered out)
    other_team = TeamFactory()
    PackageListingFactory(
        review_status=PackageListingReviewStatus.rejected,
        package_kwargs=dict(owner=other_team),
    )

    api_client.force_authenticate(user)
    response = api_client.get(get_user_rejected_listings_url())

    assert response.status_code == 200
    data = response.json()

    # Only the two rejected listings owned by the user's team should be returned
    assert data["count"] == 2
    names = {r["package_name"] for r in data["results"]}
    assert expected1.package.name in names
    assert expected2.package.name in names

    # Verify each result has the correct status and owner
    for item in data["results"]:
        assert item["review_status"] == PackageListingReviewStatus.rejected
        assert item["package_owner"] == team.name
