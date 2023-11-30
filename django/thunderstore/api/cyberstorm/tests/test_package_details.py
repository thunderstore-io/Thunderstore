from datetime import datetime

import pytest
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views.package_detail import (
    get_custom_package_detail_listing,
)
from thunderstore.community.factories import (
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
    TeamMemberFactory,
)


@pytest.mark.django_db
def test_get_custom_package_detail_listing__returns_objects_matching_args() -> None:
    expected = PackageListingFactory()
    PackageListingFactory(package_=expected.package)  # Different Community
    PackageListingFactory(
        community=expected.community,
        package_kwargs={"name": expected.package.name},
    )  # Different Namespace
    PackageListingFactory(
        community=expected.community,
        package_kwargs={"namespace": expected.package.namespace},
    )  # Different Package name

    actual = get_custom_package_detail_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name,
    )

    assert actual.community.identifier == expected.community.identifier
    assert actual.package.namespace.name == expected.package.namespace.name
    assert actual.package.name == expected.package.name


@pytest.mark.django_db
def test_get_custom_package_detail_listing__treats_package_name_as_case_insensitive() -> None:
    expected = PackageListingFactory()

    requested_as_uppercase = get_custom_package_detail_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name.upper(),
    )
    requested_as_lowercase = get_custom_package_detail_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name.lower(),
    )

    assert requested_as_uppercase.package.name == expected.package.name
    assert requested_as_lowercase.package.name == expected.package.name


@pytest.mark.django_db
def test_get_custom_package_detail_listing__annotates_downloads_and_ratings() -> None:
    listing = PackageListingFactory(package_version_kwargs={"downloads": 100})
    PackageVersionFactory(
        package=listing.package,
        version_number="1.0.1",
        downloads=20,
    )
    PackageVersionFactory(
        package=listing.package,
        version_number="1.0.2",
        downloads=3,
    )

    [PackageRatingFactory(package=listing.package) for _ in range(3)]

    actual = get_custom_package_detail_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.download_count == 123
    assert actual.rating_count == 3


@pytest.mark.django_db
def test_get_custom_package_detail_listing__augments_listing_with_dependant_count() -> None:
    listing = PackageListingFactory()
    dependant_count = 5

    for _ in range(dependant_count):
        dependant = PackageVersionFactory()
        dependant.dependencies.add(listing.package.latest)

    actual = get_custom_package_detail_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.dependant_count == dependant_count


@pytest.mark.django_db
def test_get_custom_package_detail_listing__augments_listing_with_dependencies_from_same_community() -> None:
    dependant = PackageListingFactory()
    dependency1 = PackageListingFactory(community=dependant.community)
    dependency2 = PackageListingFactory()
    dependency3 = PackageListingFactory(community=dependant.community)
    dependant.package.latest.dependencies.set(
        [
            dependency1.package.latest,
            dependency2.package.latest,
            dependency3.package.latest,
        ],
    )

    actual = get_custom_package_detail_listing(
        dependant.community.identifier,
        dependant.package.namespace.name,
        dependant.package.name.upper(),
    )

    assert actual.dependencies.count() == 2
    assert dependency1.package.latest in actual.dependencies
    assert dependency2.package.latest not in actual.dependencies
    assert dependency3.package.latest in actual.dependencies


@pytest.mark.django_db
def test_package_detail_view__returns_info(api_client: APIClient) -> None:
    community = CommunityFactory()
    category = PackageCategoryFactory(community=community)
    listing = PackageListingFactory(
        community=community,
        categories=[category],
        package_kwargs={"is_pinned": True},
        package_version_kwargs={
            "changelog": " ",
            "downloads": 99,
            "website_url": "https://thunderstore.io/",
        },
    )
    latest = listing.package.latest
    dependant = PackageVersionFactory()
    dependant.dependencies.set([latest])
    dependency = PackageListingFactory(community=community)
    latest.dependencies.set([dependency.package.latest])
    [PackageRatingFactory(package=listing.package) for _ in range(8)]
    owner = TeamMemberFactory(team=listing.package.owner, role="owner")
    member = TeamMemberFactory(team=listing.package.owner, role="member")

    response = api_client.get(
        f"/api/cyberstorm/package/{community.identifier}/{listing.package.namespace}/{listing.package.name}/",
    )
    actual = response.json()

    assert len(actual["categories"]) == 1
    assert actual["categories"][0]["id"] == str(category.id)
    assert actual["community_identifier"] == community.identifier
    assert actual["community_name"] == community.name
    assert actual["datetime_created"] == _date_to_z(latest.date_created)
    assert actual["dependant_count"] == 1
    assert len(actual["dependencies"]) == 1
    assert actual["dependencies"][0]["community_identifier"] == community.identifier
    assert actual["dependencies"][0]["namespace"] == dependency.package.namespace.name
    assert actual["dependencies"][0]["name"] == dependency.package.name
    assert actual["description"] == latest.description
    assert actual["download_count"] == 99
    assert actual["download_url"] == latest.full_download_url
    assert actual["full_version_name"] == latest.full_version_name
    assert actual["has_changelog"] == bool(latest.changelog.strip())
    assert actual["icon_url"] == latest.icon.url
    assert actual["install_url"] == latest.install_url
    assert actual["is_deprecated"] == listing.package.is_deprecated
    assert actual["is_nsfw"] == listing.has_nsfw_content
    assert actual["is_pinned"] == listing.package.is_pinned
    assert actual["last_updated"] == _date_to_z(listing.package.date_updated)
    assert actual["latest_version_number"] == latest.version_number
    assert actual["name"] == listing.package.name
    assert actual["namespace"] == listing.package.namespace.name
    assert actual["rating_count"] == 8
    assert actual["size"] == latest.file_size
    assert actual["team"]["name"] == listing.package.owner.name
    assert len(actual["team"]["members"]) == 2
    assert actual["team"]["members"][0]["identifier"] == owner.user.id
    assert actual["team"]["members"][0]["role"] == "owner"
    assert actual["team"]["members"][1]["identifier"] == member.user.id
    assert actual["team"]["members"][1]["role"] == "member"
    assert actual["website_url"] == latest.website_url


def _date_to_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
