from typing import Dict, List, Union

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache
from thunderstore.community.factories import CommunitySiteFactory, PackageListingFactory
from thunderstore.community.models import (
    PackageCategory,
    PackageListingReviewStatus,
    PackageListingSection,
)
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.frontend.api.experimental.views import CommunityPackageListApiView
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
)


@pytest.fixture(scope="module", autouse=True)
def clear_pagination_cache():
    invalidate_cache(CacheBustCondition.any_package_updated)


@pytest.mark.django_db
def test_only_packages_listed_in_community_are_returned(api_client: APIClient) -> None:
    listing1 = PackageListingFactory()
    PackageListingFactory()

    data = __query_api(api_client, listing1.community.identifier)

    __assert_packages_by_listings(data, listing1)


@pytest.mark.django_db
def test_only_active_packages_are_returned(api_client: APIClient) -> None:
    listing1 = PackageListingFactory(package_kwargs={"is_active": False})
    PackageListingFactory()

    data = __query_api(api_client, listing1.community.identifier)

    assert len(data["packages"]) == 0


@pytest.mark.django_db
def test_only_community_listings_for_correct_community_are_included_in_queryset() -> None:
    """
    Due to the implementation, test case
    test_only_packages_listed_in_community_are_returned might
    incorrectly pass sometimes when data is returned from the database
    in a fortunate order. That test case still has its uses, since this
    one only checks a small part of the data fetching implementation.
    """
    listing1 = PackageListingFactory()
    listing2 = PackageListingFactory(package_=listing1.package)

    qs1 = CommunityPackageListApiView().get_queryset(listing1.community)
    qs2 = CommunityPackageListApiView().get_queryset(listing2.community)

    assert len(qs1.all()) == 1
    assert len(qs1.all()[0].community_listings.all()) == 1
    assert (
        qs1.all()[0].community_listings.all()[0].community.name
        == listing1.community.name
    )
    assert len(qs2.all()) == 1
    assert len(qs2.all()[0].community_listings.all()) == 1
    assert (
        qs2.all()[0].community_listings.all()[0].community.name
        == listing2.community.name
    )


@pytest.mark.django_db
def test_rejected_packages_are_not_returned(api_client: APIClient) -> None:
    listing1 = PackageListingFactory(
        review_status=PackageListingReviewStatus.unreviewed
    )
    listing2 = PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.approved
    )
    PackageListingFactory(
        community_=listing1.community, review_status=PackageListingReviewStatus.rejected
    )

    data = __query_api(api_client, listing1.community.identifier)

    __assert_packages_by_listings(data, [listing2, listing1])


@pytest.mark.django_db
def test_only_approved_packages_are_returned_when_approval_is_required(
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

    data = __query_api(api_client, listing1.community.identifier)

    __assert_packages_by_listings(data, listing2)


@pytest.mark.django_db
def test_deprecated_packages_are_returned_only_when_requested(
    api_client: APIClient,
) -> None:
    active = PackageListingFactory()
    PackageListingFactory(
        community_=active.community, package_kwargs={"is_deprecated": True}
    )

    data = __query_api(api_client, active.community.identifier)

    __assert_packages_by_listings(data, active)

    data = __query_api(api_client, active.community.identifier, "deprecated=on")

    assert len(data["packages"]) == 2


@pytest.mark.django_db
def test_nsfw_packages_are_returned_only_when_requested(api_client: APIClient) -> None:
    sfw = PackageListingFactory()
    PackageListingFactory(community_=sfw.community, has_nsfw_content=True)

    data = __query_api(api_client, sfw.community.identifier)

    __assert_packages_by_listings(data, sfw)

    data = __query_api(api_client, sfw.community.identifier, "nsfw=true")

    assert len(data["packages"]) == 2


@pytest.mark.django_db
def test_packages_are_filtered_by_required_categories(api_client: APIClient) -> None:
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

    data = __query_api(
        api_client, site.community.identifier, f"included_categories={cat1.slug}"
    )

    __assert_packages_by_listings(data, pl2)

    data = __query_api(
        api_client,
        site.community.identifier,
        f"included_categories={cat1.slug}&included_categories={cat2.slug}",
    )

    __assert_packages_by_listings(data, [pl3, pl2])


@pytest.mark.django_db
def test_packages_are_filtered_by_excluded_categories(api_client: APIClient) -> None:
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

    data = __query_api(
        api_client, site.community.identifier, f"excluded_categories={cat1.slug}"
    )

    __assert_packages_by_listings(data, [pl3, pl1])

    data = __query_api(
        api_client,
        site.community.identifier,
        f"excluded_categories={cat1.slug}&excluded_categories={cat2.slug}",
    )

    __assert_packages_by_listings(data, pl1)


@pytest.mark.django_db
def test_packages_are_filtered_by_sections(api_client: APIClient) -> None:
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

    data = __query_api(api_client, site.community.identifier, f"section={section.slug}")

    __assert_packages_by_listings(data, expected)


@pytest.mark.django_db
def test_packages_are_filtered_by_query(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(community_=site.community)
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(
        api_client, site.community.identifier, f"q={listing1.package.name}"
    )

    __assert_packages_by_listings(data, listing1)

    data = __query_api(
        api_client, site.community.identifier, f"q={listing2.package.owner.name}"
    )

    __assert_packages_by_listings(data, listing2)

    data = __query_api(
        api_client,
        site.community.identifier,
        f"q={listing3.package.latest.description}",
    )

    __assert_packages_by_listings(data, listing3)


@pytest.mark.django_db
def test_packages_are_ordered_by_update_date_by_default(api_client: APIClient) -> None:
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

    data = __query_api(api_client, site.community.identifier)

    __assert_packages_by_listings(data, [listing2, listing3, listing1])


@pytest.mark.django_db
def test_packages_can_be_ordered_by_creation_date(api_client: APIClient) -> None:
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

    data = __query_api(api_client, site.community.identifier, "ordering=newest")

    __assert_packages_by_listings(data, [listing2, listing1, listing3])


@pytest.mark.django_db
def test_paginated_results_are_cached(api_client: APIClient) -> None:
    # First request should fetch fresh data.
    listing = PackageListingFactory(package_version_kwargs={"downloads": 1})

    data = __query_api(api_client, listing.community.identifier)

    assert len(data["packages"]) == 1
    assert data["packages"][0]["download_count"] == 1

    # Changes shouldn't be returned until cache is busted.
    listing.package.latest.downloads = 3
    listing.package.latest.save()

    data = __query_api(api_client, listing.community.identifier)

    assert len(data["packages"]) == 1
    assert data["packages"][0]["download_count"] == 1

    # Manual cache busting should update the results.
    invalidate_cache(CacheBustCondition.any_package_updated)

    data = __query_api(api_client, listing.community.identifier)

    assert len(data["packages"]) == 1
    assert data["packages"][0]["download_count"] == 3


@pytest.mark.django_db
def test_packages_can_be_ordered_by_download_count(api_client: APIClient) -> None:
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

    data = __query_api(
        api_client, site.community.identifier, "ordering=most-downloaded"
    )

    __assert_packages_by_listings(data, [listing3, listing2, listing1])

    # Downloads of all versions are counted towards package's downloads.
    PackageVersionFactory(
        package=listing1.package, downloads=9001, version_number="1.0.1"
    )

    # Double check that results are not updated before the cache is busted.
    data = __query_api(
        api_client, site.community.identifier, "ordering=most-downloaded"
    )

    __assert_packages_by_listings(data, [listing3, listing2, listing1])

    # Changes should be visible after cache busting.
    invalidate_cache(CacheBustCondition.any_package_updated)

    data = __query_api(
        api_client, site.community.identifier, "ordering=most-downloaded"
    )

    __assert_packages_by_listings(data, [listing1, listing3, listing2])


@pytest.mark.django_db
def test_packages_can_be_ordered_by_rating(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(community_=site.community)
    listing3 = PackageListingFactory(community_=site.community)
    PackageRatingFactory(package=listing1.package)
    PackageRatingFactory(package=listing3.package)
    PackageRatingFactory(package=listing3.package)

    data = __query_api(api_client, site.community.identifier, "ordering=top-rated")

    __assert_packages_by_listings(data, [listing3, listing1, listing2])


@pytest.mark.django_db
def test_pinned_packages_are_returned_first(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(
        community_=site.community, package_kwargs={"is_pinned": True}
    )
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(api_client, site.community.identifier)

    __assert_packages_by_listings(data, [listing2, listing3, listing1])


@pytest.mark.django_db
def test_deprecated_packages_are_returned_last(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site.community)
    listing2 = PackageListingFactory(
        community_=site.community, package_kwargs={"is_deprecated": True}
    )
    listing3 = PackageListingFactory(community_=site.community)

    data = __query_api(api_client, site.community.identifier, "deprecated=1")

    __assert_packages_by_listings(data, [listing3, listing1, listing2])


@pytest.mark.django_db
def test_pagination(api_client: APIClient) -> None:
    site = CommunitySiteFactory()

    for i in range(25):
        PackageListingFactory(community_=site.community)

    data = __query_api(api_client, site.community.identifier)

    assert len(data["packages"]) == 24
    assert data["has_more_pages"]

    page1_packages = [p["package_name"] for p in data["packages"]]
    data = __query_api(api_client, site.community.identifier, "page=2")

    assert len(data["packages"]) == 1
    assert data["packages"][0]["package_name"] not in page1_packages
    assert not data["has_more_pages"]


@pytest.mark.django_db
def test_page_index_error(api_client: APIClient) -> None:
    site = CommunitySiteFactory()
    url = reverse(
        "api:experimental:frontend.community.packages",
        kwargs={"community_identifier": site.community.identifier},
    )

    response = api_client.get(f"{url}?page=2")

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Page index error")

    for i in range(25):
        PackageListingFactory(community_=site.community)

    invalidate_cache(CacheBustCondition.any_package_updated)
    response = api_client.get(f"{url}?page=2")

    assert response.status_code == 200


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

    assert len(data["packages"]) == len(expected)

    for i, actual in enumerate(data["packages"]):
        assert actual["package_name"] == expected[i].package.name


def __query_api(client: APIClient, identifier: str, query: str = "") -> Dict:
    url = reverse(
        "api:experimental:frontend.community.packages",
        kwargs={"community_identifier": identifier},
    )
    response = client.get(f"{url}?{query}")
    assert response.status_code == 200
    return response.json()
