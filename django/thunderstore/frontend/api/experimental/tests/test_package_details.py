from typing import Dict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
)


@pytest.mark.django_db
def test_inactive_package_returns_404(api_client: APIClient) -> None:
    listing = PackageListingFactory(package_kwargs={"is_active": False})

    response = api_client.get(__url_for_listing(listing))

    assert response.status_code == 404


@pytest.mark.django_db
def test_inactive_package_version_returns_404(api_client: APIClient) -> None:
    listing = PackageListingFactory(package_version_kwargs={"is_active": False})

    response = api_client.get(__url_for_listing(listing))

    assert response.status_code == 404


@pytest.mark.django_db
def test_unlisted_community_returns_404(api_client: APIClient) -> None:
    listing = PackageListingFactory(community_kwargs={"is_listed": False})

    response = api_client.get(__url_for_listing(listing))

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "require_approval", "http_code"),
    (
        (PackageListingReviewStatus.approved, False, 200),
        (PackageListingReviewStatus.approved, True, 200),
        (PackageListingReviewStatus.unreviewed, False, 200),
        (PackageListingReviewStatus.unreviewed, True, 404),
        (PackageListingReviewStatus.rejected, False, 404),
        (PackageListingReviewStatus.rejected, True, 404),
    ),
)
def test_listing_approval_status_is_checked(
    api_client: APIClient,
    status: PackageListingReviewStatus,
    require_approval: bool,
    http_code: int,
) -> None:
    listing = PackageListingFactory(
        review_status=status,
        community_kwargs={"require_package_listing_approval": require_approval},
    )

    response = api_client.get(__url_for_listing(listing))

    assert response.status_code == http_code


@pytest.mark.django_db
def test_dependant_count_is_annotated_correctly(api_client: APIClient) -> None:
    dependency = PackageListingFactory()
    dependency.package.latest.dependants.set(
        [PackageVersionFactory(), PackageVersionFactory()]
    )

    data = __query_api(api_client, dependency)

    assert data["dependant_count"] == 2


@pytest.mark.django_db
def test_downloads_count_is_annotated_correctly(api_client: APIClient) -> None:
    listing = PackageListingFactory(package_version_kwargs={"downloads": 0})
    PackageVersionFactory(package=listing.package, downloads=1, version_number="1.0.1")
    PackageVersionFactory(package=listing.package, downloads=2, version_number="1.0.2")

    data = __query_api(api_client, listing)

    assert data["download_count"] == 3


@pytest.mark.django_db
@pytest.mark.parametrize("rating_count", (0, 1, 2))
def test_rating_is_annotated_correctly(
    api_client: APIClient, rating_count: int
) -> None:
    listing = PackageListingFactory()
    for i in range(rating_count):
        PackageRatingFactory(package=listing.package)

    data = __query_api(api_client, listing)

    assert data["rating_score"] == rating_count


@pytest.mark.django_db
def test_dependencies_for_correct_version_are_returned(api_client: APIClient) -> None:
    listing = PackageListingFactory()
    old = listing.package.latest
    newer = PackageVersionFactory(package=old.package, version_number="2.0.0")
    dependency1 = PackageListingFactory()
    dependency2 = PackageListingFactory()
    old.dependencies.set([dependency1.package.latest])
    newer.dependencies.set([dependency2.package.latest])

    data = __query_api(api_client, listing)

    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["package_name"] == dependency2.package.name


@pytest.mark.django_db
def test_dependencies_refer_to_preferred_community(api_client: APIClient) -> None:
    alternative_dependency = PackageListingFactory()
    preferred_dependency = PackageListingFactory(package=alternative_dependency.package)
    dependant = PackageListingFactory(community=preferred_dependency.community)
    dependant.package.latest.dependencies.set([alternative_dependency.package.latest])

    data = __query_api(api_client, dependant)

    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["package_name"] == preferred_dependency.package.name
    assert (
        data["dependencies"][0]["community_identifier"]
        == preferred_dependency.community.identifier
    )
    assert (
        data["community_identifier"] == data["dependencies"][0]["community_identifier"]
    )


@pytest.mark.django_db
def test_dependencies_fallback_to_any_community(api_client: APIClient) -> None:
    dependency = PackageListingFactory()
    dependant = PackageListingFactory()
    dependant.package.latest.dependencies.set([dependency.package.latest])

    data = __query_api(api_client, dependant)

    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["package_name"] == dependency.package.name
    assert (
        data["dependencies"][0]["community_identifier"]
        == dependency.community.identifier
    )
    assert (
        data["community_identifier"] != data["dependencies"][0]["community_identifier"]
    )


@pytest.mark.django_db
def test_dependencies_without_package_listings_contain_nones(
    api_client: APIClient,
) -> None:
    dependency = PackageVersionFactory()
    dependant = PackageListingFactory()
    dependant.package.latest.dependencies.set([dependency])

    data = __query_api(api_client, dependant)

    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["community_name"] is None
    assert data["dependencies"][0]["community_identifier"] is None


@pytest.mark.django_db
def test_versions_are_sorted_by_version_number(api_client: APIClient) -> None:
    listing = PackageListingFactory(package_version_kwargs={"version_number": "0.1.0"})
    v010 = listing.package.latest
    v100 = PackageVersionFactory(package=listing.package, version_number="1.0.0")
    v200 = PackageVersionFactory(package=listing.package, version_number="2.0.0")
    v110 = PackageVersionFactory(package=listing.package, version_number="1.1.0")
    v101 = PackageVersionFactory(package=listing.package, version_number="1.0.1")

    data = __query_api(api_client, listing)

    assert len(data["versions"]) == 5
    assert data["versions"][0]["version_number"] == v200.version_number
    assert data["versions"][1]["version_number"] == v110.version_number
    assert data["versions"][2]["version_number"] == v101.version_number
    assert data["versions"][3]["version_number"] == v100.version_number
    assert data["versions"][4]["version_number"] == v010.version_number


@pytest.mark.django_db
def test_inactive_versions_are_excluded(api_client: APIClient) -> None:
    listing = PackageListingFactory()
    original = listing.package.latest
    active = PackageVersionFactory(package=listing.package, version_number="1.0.1")
    PackageVersionFactory(
        package=listing.package, version_number="1.0.2", is_active=False
    )

    data = __query_api(api_client, listing)

    assert len(data["versions"]) == 2
    assert data["versions"][0]["version_number"] == active.version_number
    assert data["versions"][1]["version_number"] == original.version_number


@pytest.mark.django_db
def test_hidden_categories_are_excluded_in_package_detail(
    api_client: APIClient,
) -> None:
    listing = PackageListingFactory()
    # Create visible and hidden categories in the same community and attach to listing
    visible = PackageCategory.objects.create(
        name="visible",
        slug="visible",
        community=listing.community,
        hidden=False,
    )
    hidden = PackageCategory.objects.create(
        name="hidden",
        slug="hidden",
        community=listing.community,
        hidden=True,
    )
    listing.categories.set([visible, hidden])

    data = __query_api(api_client, listing)

    assert {c["slug"] for c in data["categories"]} == {"visible"}


def __query_api(client: APIClient, listing: PackageListing) -> Dict:
    response = client.get(__url_for_listing(listing))
    assert response.status_code == 200
    return response.json()


def __url_for_listing(listing: PackageListing) -> str:
    return reverse(
        "api:experimental:frontend.community.package",
        kwargs={
            "community_identifier": listing.community.identifier,
            "package_namespace": listing.package.namespace.name,
            "package_name": listing.package.name,
        },
    )
