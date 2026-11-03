import pytest
from rest_framework.test import APIClient

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.factories import (
    PackageFactory,
    PackageRatingFactory,
    PackageVersionFactory,
)
from thunderstore.repository.models import Package
from thunderstore.repository.models.team import Team


def create_team_package(team: Team, is_active: bool = True) -> Package:
    """
    Create a package owned by the team with a single active version

    :param team: The team owning the package
    :param is_active: Whether the package itself is active
    :return: The created package
    """
    package = PackageFactory.create(
        owner=team,
        namespace=team.get_namespace(),
        is_active=is_active,
    )
    PackageVersionFactory.create(package=package, name=package.name, is_active=True)
    return package


def create_listing(
    community: Community,
    package: Package,
    review_status: str = PackageListingReviewStatus.unreviewed,
) -> PackageListing:
    """
    Create a listing for the package in the community

    :param community: The community to list the package in
    :param package: The package to list
    :param review_status: The review status of the listing
    :return: The created listing
    """
    return PackageListingFactory.create(
        community_=community,
        package_=package,
        review_status=review_status,
    )


def get_communities(api_client: APIClient, team_name: str):
    """
    Fetch the team communities endpoint

    :param api_client: The API client to request with
    :param team_name: The name of the team
    :return: The response
    """
    return api_client.get(f"/api/cyberstorm/team/{team_name}/communities/")


@pytest.mark.django_db
def test_team_communities__for_team_without_packages__returns_empty_list(
    api_client: APIClient,
    team: Team,
):
    response = get_communities(api_client, team.name)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_team_communities__returns_communities_with_package_counts(
    api_client: APIClient,
    team: Team,
):
    alpha = CommunityFactory(name="Alpha")
    beta = CommunityFactory(name="Beta")
    create_listing(beta, create_team_package(team))
    create_listing(alpha, create_team_package(team))
    create_listing(alpha, create_team_package(team))

    response = get_communities(api_client, team.name)
    result = response.json()

    assert response.status_code == 200
    assert [c["identifier"] for c in result] == [alpha.identifier, beta.identifier]
    assert [c["name"] for c in result] == ["Alpha", "Beta"]
    assert [c["package_count"] for c in result] == [2, 1]
    assert "community_icon_url" in result[0]


@pytest.mark.django_db
def test_team_communities__returns_download_and_rating_totals(
    api_client: APIClient,
    team: Team,
):
    community = CommunityFactory()
    first = create_team_package(team)
    second = create_team_package(team)
    first.versions.update(downloads=10)
    PackageVersionFactory.create(
        package=first, name=first.name, version_number="2.0.0", downloads=5
    )
    second.versions.update(downloads=7)
    PackageRatingFactory.create(package=first)
    PackageRatingFactory.create(package=first)
    PackageRatingFactory.create(package=second)
    create_listing(community, first)
    create_listing(community, second)

    response = get_communities(api_client, team.name)
    result = response.json()

    assert response.status_code == 200
    assert len(result) == 1
    assert result[0]["package_count"] == 2
    assert result[0]["download_count"] == 22
    assert result[0]["rating_count"] == 3


@pytest.mark.django_db
def test_team_communities__without_downloads_or_ratings__returns_zeros(
    api_client: APIClient,
    team: Team,
):
    community = CommunityFactory()
    create_listing(community, create_team_package(team))

    response = get_communities(api_client, team.name)
    result = response.json()

    assert response.status_code == 200
    assert result[0]["download_count"] == 0
    assert result[0]["rating_count"] == 0


@pytest.mark.django_db
def test_team_communities__excludes_other_teams_packages(
    api_client: APIClient,
    team: Team,
):
    other_team = Team.create(name="Other_Team")
    community = CommunityFactory()
    create_listing(community, create_team_package(other_team))

    response = get_communities(api_client, team.name)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_team_communities__excludes_inactive_packages(
    api_client: APIClient,
    team: Team,
):
    community = CommunityFactory()
    create_listing(community, create_team_package(team, is_active=False))

    response = get_communities(api_client, team.name)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_team_communities__excludes_rejected_listings(
    api_client: APIClient,
    team: Team,
):
    community = CommunityFactory()
    create_listing(
        community,
        create_team_package(team),
        review_status=PackageListingReviewStatus.rejected,
    )

    response = get_communities(api_client, team.name)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("review_status", "expected_count"),
    (
        (PackageListingReviewStatus.unreviewed, 0),
        (PackageListingReviewStatus.approved, 1),
    ),
)
def test_team_communities__in_community_requiring_approval__counts_approved_only(
    api_client: APIClient,
    team: Team,
    review_status: str,
    expected_count: int,
):
    community = CommunityFactory(require_package_listing_approval=True)
    create_listing(community, create_team_package(team), review_status=review_status)

    response = get_communities(api_client, team.name)
    result = response.json()

    assert response.status_code == 200
    assert len(result) == expected_count


@pytest.mark.django_db
def test_team_communities__for_nonexisting_team__returns_404(
    api_client: APIClient,
):
    response = get_communities(api_client, "bad")

    assert response.status_code == 404


@pytest.mark.django_db
def test_team_communities__for_inactive_team__returns_404(
    api_client: APIClient,
    team: Team,
):
    team.is_active = False
    team.save()

    response = get_communities(api_client, team.name)

    assert response.status_code == 404
