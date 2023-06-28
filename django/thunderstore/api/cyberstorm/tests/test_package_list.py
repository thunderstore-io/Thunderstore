from typing import Dict, List, Union

import pytest
from django.db.models import Sum
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunitySiteFactory, PackageListingFactory
from thunderstore.community.models import PackageCategory, PackageListingSection
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.factories import (
    PackageFactory,
    PackageRatingFactory,
    PackageVersionFactory,
    TeamFactory,
    TeamMemberFactory,
)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_paginate_index_error(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()

    for i in range(25):
        PackageListingFactory(community_=site.community)

    data = __query_api(api_client)

    assert data["current"] == 1
    assert data["final"] == 2
    assert data["total"] == 25
    assert data["count"] == 20
    assert len(data["results"]) == 20

    __query_api(api_client, "page=3", response_status_code=404)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_only_active_packages_are_returned(
    api_client: APIClient,
) -> None:
    PackageListingFactory(package_kwargs={"is_active": False})
    PackageListingFactory()

    data = __query_api(api_client)

    assert len(data["results"]) == 1


@pytest.mark.django_db
def test_api_cyberstorm_package_list_rejected_packages_are_not_returned(
    api_client: APIClient,
) -> None:
    listing1 = PackageListingFactory(
        review_status=PackageListingReviewStatus.unreviewed
    )
    listing2 = PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.approved
    )
    listing3 = PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.rejected
    )

    data = __query_api(api_client)

    __assert_packages_by_listings(data, [listing2, listing1])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_only_approved_packages_are_returned_when_approval_is_required(
    api_client: APIClient,
) -> None:
    listing1 = PackageListingFactory(
        review_status=PackageListingReviewStatus.unreviewed
    )
    listing1.community.require_package_listing_approval = True
    listing1.community.save()
    listing2 = PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.approved
    )
    PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.rejected
    )

    data = __query_api(api_client)

    __assert_packages_by_listings(data, listing2)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_deprecated_packages_are_returned_only_when_requested(
    api_client: APIClient,
) -> None:
    active = PackageListingFactory()
    PackageListingFactory(
        community_=active.community, package_kwargs={"is_deprecated": True}
    )

    data = __query_api(api_client)

    __assert_packages_by_listings(data, active)

    data = __query_api(api_client, "include_deprecated=on")

    assert len(data["results"]) == 2


@pytest.mark.django_db
def test_api_cyberstorm_package_list_nsfw_packages_are_returned_only_when_requested(
    api_client: APIClient,
) -> None:
    sfw = PackageListingFactory()
    nsfw = PackageListingFactory(community_=sfw.community, has_nsfw_content=True)

    data = __query_api(api_client, "include_nsfw=true")
    __assert_packages_by_listings(data, [nsfw, sfw])

    data = __query_api(api_client)
    __assert_packages_by_listings(data, sfw)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_required_categories(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    cat1 = PackageCategory.objects.create(
        name="c1", slug="c1", community=site.community
    )
    cat2 = PackageCategory.objects.create(
        name="c2", slug="c2", community=site.community
    )
    PackageListingFactory(community_=site.community)
    pl2 = PackageListingFactory(community_=site.community, categories=[cat1])
    pl3 = PackageListingFactory(community_=site.community, categories=[cat2])

    data = __query_api(api_client, f"included_categories={cat1.slug}")

    __assert_packages_by_listings(data, pl2)

    data = __query_api(
        api_client,
        f"included_categories={cat1.slug}&included_categories={cat2.slug}",
    )

    __assert_packages_by_listings(data, [pl3, pl2])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_excluded_categories(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    cat1 = PackageCategory.objects.create(
        name="c1", slug="c1", community=site.community
    )
    cat2 = PackageCategory.objects.create(
        name="c2", slug="c2", community=site.community
    )
    pl1 = PackageListingFactory(community_=site.community)
    PackageListingFactory(community_=site.community, categories=[cat1])
    pl3 = PackageListingFactory(community_=site.community, categories=[cat2])

    data = __query_api(api_client, f"excluded_categories={cat1.slug}")

    __assert_packages_by_listings(data, [pl3, pl1])

    data = __query_api(
        api_client,
        f"excluded_categories={cat1.slug}&excluded_categories={cat2.slug}",
    )

    __assert_packages_by_listings(data, pl1)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_sections(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    required = PackageCategory.objects.create(
        name="r", slug="r", community=site.community
    )
    excluded = PackageCategory.objects.create(
        name="e", slug="e", community=site.community
    )
    irrelevant = PackageCategory.objects.create(
        name="i", slug="i", community=site.community
    )
    section = PackageListingSection.objects.create(
        name="Modpacks", slug="modpacks", community=site.community
    )
    section.require_categories.set([required])
    section.exclude_categories.set([excluded])
    expected = PackageListingFactory(community_=site.community, categories=[required])
    PackageListingFactory(community_=site.community, categories=[required, excluded])
    PackageListingFactory(community_=site.community, categories=[excluded])
    PackageListingFactory(community_=site.community, categories=[irrelevant])

    data = __query_api(api_client, f"section={section.slug}")

    __assert_packages_by_listings(data, expected)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_section_does_not_exist(
    api_client: APIClient,
) -> None:
    data = __query_api(api_client, "section=bad", response_status_code=404)
    assert data["detail"] == "Not found."


@pytest.mark.django_db
def test_packages_are_filtered_by_query(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(community_=site.community)
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(api_client, f"q={listing1.package.name}")

    __assert_packages_by_listings(data, listing1)

    data = __query_api(api_client, f"q={listing2.package.owner.name}")

    __assert_packages_by_listings(data, listing2)

    data = __query_api(
        api_client,
        f"q={listing3.package.latest.description}",
    )

    __assert_packages_by_listings(data, listing3)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_community_id(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    site2 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(community_=site2.community)

    data = __query_api(
        api_client,
        f"community_id={'bad'}",
    )
    assert len(data["results"]) == 0

    data = __query_api(
        api_client,
        f"community_id={listing1.community.identifier}",
    )
    __assert_packages_by_listings(data, listing1)

    data = __query_api(
        api_client,
        f"community_id={listing2.community.identifier}",
    )
    __assert_packages_by_listings(data, listing2)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_namespace(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)

    data = __query_api(
        api_client,
        f"namespace={'bad'}",
    )
    assert len(data["results"]) == 0

    data = __query_api(
        api_client,
        f"namespace={listing1.package.namespace.name}",
    )
    __assert_packages_by_listings(data, listing1)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_team_id(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)

    data = __query_api(
        api_client,
        f"team_id={'bad'}",
    )
    assert len(data["results"]) == 0

    data = __query_api(
        api_client,
        f"team_id={listing1.package.owner.name}",
    )
    __assert_packages_by_listings(data, listing1)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_user_id(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    team = TeamFactory()
    TeamMemberFactory(team=team)
    package = PackageFactory(owner=team)
    PackageVersionFactory(package=package, downloads=9001, version_number="1.0.1")
    listing1 = PackageListingFactory(package_=package, community_=site.community)

    data = __query_api(api_client, "user_id=bad")
    assert len(data["results"]) == 0

    data = __query_api(
        api_client,
        f"user_id={listing1.package.owner.members.first().user.username}",
    )
    __assert_packages_by_listings(data, listing1)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_filtered_by_package_id(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)

    data = __query_api(
        api_client,
        f"package_id={'bad'}",
    )
    assert len(data["results"]) == 0

    data = __query_api(
        api_client,
        f"package_id={listing1.package.name}",
    )
    __assert_packages_by_listings(data, listing1)


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_are_ordered_by_update_date_by_default(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_updated": "2022-02-02 01:23:45Z"},
    )
    listing2 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_updated": "2022-02-22 01:23:45Z"},
    )
    listing3 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_updated": "2022-02-12 01:23:45Z"},
    )

    data = __query_api(api_client)

    __assert_packages_by_listings(data, [listing2, listing3, listing1])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_can_be_ordered_by_creation_date(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_created": "2022-02-12 01:23:45Z"},
    )
    listing2 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_created": "2022-02-22 01:23:45Z"},
    )
    listing3 = PackageListingFactory(
        community_=site.community,
        package_kwargs={"date_created": "2022-02-02 01:23:45Z"},
    )

    data = __query_api(api_client, "ordering=newest")

    __assert_packages_by_listings(data, [listing2, listing1, listing3])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_can_be_ordered_by_download_count(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(
        community_=site.community, package_version_kwargs={"downloads": 0}
    )
    listing2 = PackageListingFactory(
        community_=site.community, package_version_kwargs={"downloads": 23}
    )
    listing3 = PackageListingFactory(
        community_=site.community, package_version_kwargs={"downloads": 42}
    )

    data = __query_api(api_client, "ordering=most-downloaded")

    __assert_packages_by_listings(data, [listing3, listing2, listing1])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_packages_can_be_ordered_by_rating(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(community_=site.community)
    listing3 = PackageListingFactory(community_=site.community)
    PackageRatingFactory(package=listing1.package)
    PackageRatingFactory(package=listing3.package)
    PackageRatingFactory(package=listing3.package)

    data = __query_api(api_client, "ordering=top-rated")

    __assert_packages_by_listings(data, [listing3, listing1, listing2])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_package_rating_and_download_counts(
    api_client: APIClient,
) -> None:

    # 1 Community
    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    listing2 = PackageListingFactory(community_=site1.community)
    listing3 = PackageListingFactory(community_=site1.community)
    PackageRatingFactory(package=listing1.package)
    PackageRatingFactory(package=listing3.package)
    PackageRatingFactory(package=listing3.package)
    assert listing1.package.package_ratings.count() == 1
    __assert_downloads(listing1, 0)

    data = __query_api(api_client, "ordering=top-rated")
    for result in data["results"]:
        if result["name"] == listing1.package.name:
            assert result["likes"] == 1
            assert result["download_count"] == 0

    # 2 Communities
    site2 = CommunitySiteFactory()
    listing4 = PackageListingFactory(
        package_=listing1.package, community_=site2.community
    )
    for x in range(1, 6):
        PackageRatingFactory(package=listing4.package)
        PackageVersionFactory(
            package=listing4.package, downloads=5, version_number=f"{1+x}.0.0"
        )

    assert listing1.package.package_ratings.count() == 6
    __assert_downloads(listing1, 25)

    assert listing4.package.package_ratings.count() == 6
    __assert_downloads(listing4, 25)

    data = __query_api(api_client, "ordering=top-rated")
    for result in data["results"]:
        if result["name"] == listing4.package.name:
            assert result["likes"] == 6
            assert result["download_count"] == 25

    # 3 Communities
    site3 = CommunitySiteFactory()
    listing5 = PackageListingFactory(
        package_=listing1.package, community_=site3.community
    )
    for x in range(1, 4):
        PackageRatingFactory(package=listing5.package)
        PackageVersionFactory(
            package=listing5.package, downloads=123, version_number=f"{6+x}.0.0"
        )

    assert listing1.package.package_ratings.count() == 9
    __assert_downloads(listing1, 394)

    assert listing4.package.package_ratings.count() == 9
    __assert_downloads(listing4, 394)

    assert listing5.package.package_ratings.count() == 9
    __assert_downloads(listing5, 394)

    data = __query_api(api_client, "ordering=top-rated")
    for result in data["results"]:
        if result["name"] == listing5.package.name:
            assert result["likes"] == 9
            assert result["download_count"] == 394

    __assert_packages_by_listings(
        data, [listing1, listing4, listing5, listing3, listing2]
    )


@pytest.mark.django_db
def test_api_cyberstorm_package_list_pinned_packages_are_returned_first(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(
        community_=site.community, package_kwargs={"is_pinned": True}
    )
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(api_client)

    __assert_packages_by_listings(data, [listing2, listing3, listing1])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_deprecated_packages_are_returned_last(
    api_client: APIClient,
) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(
        community_=site.community, package_kwargs={"is_deprecated": True}
    )
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(api_client, "include_deprecated=1")

    __assert_packages_by_listings(data, [listing3, listing1, listing2])


@pytest.mark.django_db
def test_api_cyberstorm_package_list_pagination(api_client: APIClient) -> None:
    site = CommunitySiteFactory()

    for i in range(25):
        PackageListingFactory(community_=site.community)

    data = __query_api(api_client)

    assert data["current"] == 1
    assert data["final"] == 2
    assert data["total"] == 25
    assert data["count"] == 20
    assert len(data["results"]) == 20

    page1_packages = [p["name"] for p in data["results"]]
    data = __query_api(api_client, "page=2")

    assert data["results"][0]["name"] not in page1_packages
    assert data["current"] == 2
    assert data["final"] == 2
    assert data["total"] == 25
    assert data["count"] == 5
    assert len(data["results"]) == 5


def __assert_packages_by_listings(
    data: Dict, listings: Union[PackageListing, List[PackageListing]]
) -> None:
    """
    Check that expected packages, identified by name, are found in results

    Note that by default the packages in the results are ordered by
    "last updated". I.e. if package.date_updated fields aren't manually
    set and no ordering parameter is given when creating the request,
    the listings passed to this function need to be in reverse creation
    order.
    """
    expected = listings if isinstance(listings, List) else [listings]

    assert len(data["results"]) == len(expected)

    for i, actual in enumerate(data["results"]):
        assert actual["name"] == expected[i].package.name


def __query_api(client: APIClient, query: str = "", response_status_code=200) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.packages",
    )
    response = client.get(f"{url}?{query}")
    assert response.status_code == response_status_code
    return response.json()


def __assert_downloads(listing, count):
    total = 0
    for x in listing.package.versions.all():
        total += x.downloads
    assert total == count
