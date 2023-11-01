from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient, APIRequestFactory

from thunderstore.api.cyberstorm.views.packages import BasePackageListApiView
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
)
from thunderstore.repository.models import Package

########################
# BasePackageListApiView
########################


def get_mock_qs(self):
    return Package.objects.all()


mock_base_package_list_api_view = patch.multiple(
    BasePackageListApiView,
    _get_base_queryset=get_mock_qs,
    _get_paginator_cache_key=Mock(return_value="cache"),
    _get_paginator_cache_vary_prefix=Mock(return_value="cache"),
    _get_request_path=Mock(return_value="packages"),
)


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_inactive_packages() -> None:
    PackageListingFactory(package_kwargs={"is_active": False})

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_deprecated_packages() -> None:
    PackageListingFactory(package_kwargs={"is_deprecated": True})

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__include_deprecated_packages() -> None:
    PackageListingFactory(package_kwargs={"is_deprecated": True})

    request = APIRequestFactory().get("/", {"deprecated": True})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_nsfw() -> None:
    PackageListingFactory(has_nsfw_content=True)

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__include_nsfw_packages() -> None:
    PackageListingFactory(has_nsfw_content=True)

    request = APIRequestFactory().get("/", {"nsfw": True})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__does_not_filter_by_categories(
    community: Community,
) -> None:
    cat = PackageCategory.objects.create(name="c", slug="c", community=community)
    PackageListingFactory(community_=community)
    PackageListingFactory(community_=community, categories=[cat])

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 2


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_including_category__filters_out_not_matched(
    community: Community,
) -> None:
    cat = PackageCategory.objects.create(name="c", slug="c", community=community)
    PackageListingFactory(community_=community, categories=[])
    included = PackageListingFactory(community_=community, categories=[cat])

    request = APIRequestFactory().get("/", {"included_categories": [cat.id]})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == included.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_excluding_category__filters_out_matched(
    community: Community,
) -> None:
    cat = PackageCategory.objects.create(name="c", slug="c", community=community)
    included = PackageListingFactory(community_=community, categories=[])
    PackageListingFactory(community_=community, categories=[cat])

    request = APIRequestFactory().get("/", {"excluded_categories": [cat.id]})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == included.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requesting_section__filters_based_on_categories(
    community: Community,
) -> None:
    required = PackageCategory.objects.create(name="r", slug="r", community=community)
    excluded = PackageCategory.objects.create(name="e", slug="e", community=community)
    irrelevant = PackageCategory.objects.create(name="i", slug="i", community=community)
    section = PackageListingSection.objects.create(
        name="Modpacks",
        slug="modpacks",
        community=community,
    )
    section.require_categories.set([required])
    section.exclude_categories.set([excluded])
    expected = PackageListingFactory(community_=community, categories=[required])
    PackageListingFactory(community_=community, categories=[required, excluded])
    PackageListingFactory(community_=community, categories=[excluded])
    PackageListingFactory(community_=community, categories=[irrelevant])

    request = APIRequestFactory().get("/", {"section": section.uuid})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == expected.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requesting_nonexisting_section__does_nothing() -> None:
    expected = PackageListingFactory()

    request = APIRequestFactory().get(
        "/",
        {"section": "decade00-0000-4000-a000-000000000000"},
    )
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == expected.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_search_is_used__filters_based_on_names_and_description(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(community_=community)
    pl2 = PackageListingFactory(community_=community)
    pl3 = PackageListingFactory(community_=community)

    request = APIRequestFactory().get("/", {"q": pl1.package.name})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == pl1.package.name

    request = APIRequestFactory().get("/", {"q": pl2.package.owner.name})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == pl2.package.name

    request = APIRequestFactory().get("/", {"q": pl3.package.latest.description})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == pl3.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__orders_packages_by_update_date(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_updated": "2022-02-02 01:23:45Z"},
    )
    pl2 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_updated": "2022-02-22 01:23:45Z"},
    )
    pl3 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_updated": "2022-02-12 01:23:45Z"},
    )

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl2.package.name
    assert response.data["results"][1]["name"] == pl3.package.name
    assert response.data["results"][2]["name"] == pl1.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__orders_packages_by_creation_date(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_created": "2022-02-02 01:23:45Z"},
    )
    pl2 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_created": "2022-02-22 01:23:45Z"},
    )
    pl3 = PackageListingFactory(
        community_=community,
        package_kwargs={"date_created": "2022-02-12 01:23:45Z"},
    )

    request = APIRequestFactory().get("/", {"ordering": "newest"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl2.package.name
    assert response.data["results"][1]["name"] == pl3.package.name
    assert response.data["results"][2]["name"] == pl1.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__orders_packages_by_download_counts(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(
        community_=community,
        package_version_kwargs={"downloads": 0},
    )
    pl2 = PackageListingFactory(
        community_=community,
        package_version_kwargs={"downloads": 23},
    )
    pl3 = PackageListingFactory(
        community_=community,
        package_version_kwargs={"downloads": 42},
    )

    request = APIRequestFactory().get("/", {"ordering": "most-downloaded"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl3.package.name
    assert response.data["results"][1]["name"] == pl2.package.name
    assert response.data["results"][2]["name"] == pl1.package.name

    # Downloads of all versions are counted towards package's downloads.
    PackageVersionFactory(package=pl1.package, downloads=9001, version_number="1.0.1")

    invalidate_cache(CacheBustCondition.any_package_updated)
    request = APIRequestFactory().get("/", {"ordering": "most-downloaded"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl1.package.name
    assert response.data["results"][1]["name"] == pl3.package.name
    assert response.data["results"][2]["name"] == pl2.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__orders_packages_by_rating_counts(
    community: Community,
) -> None:
    middle = PackageListingFactory(community_=community)
    bottom = PackageListingFactory(community_=community)
    top = PackageListingFactory(community_=community)
    PackageRatingFactory(package=middle.package)
    PackageRatingFactory(package=top.package)
    PackageRatingFactory(package=top.package)

    request = APIRequestFactory().get("/", {"ordering": "top-rated"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == top.package.name
    assert response.data["results"][1]["name"] == middle.package.name
    assert response.data["results"][2]["name"] == bottom.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__unknown_ordering_parameter__returns_error(
    community: Community,
) -> None:
    request = APIRequestFactory().get("/", {"ordering": "color"})
    response = BasePackageListApiView().dispatch(request)

    assert "ordering" in response.data
    assert "is not a valid choice" in str(response.data["ordering"])


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__always__returns_pinned_packages_first(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(community_=community)
    pl2 = PackageListingFactory(
        community_=community,
        package_kwargs={"is_pinned": True},
    )
    pl3 = PackageListingFactory(community_=community)

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl2.package.name
    assert response.data["results"][1]["name"] == pl3.package.name
    assert response.data["results"][2]["name"] == pl1.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__always__returns_deprecated_packages_last(
    community: Community,
) -> None:
    pl1 = PackageListingFactory(community_=community)
    pl2 = PackageListingFactory(
        community_=community,
        package_kwargs={"is_deprecated": True},
    )
    pl3 = PackageListingFactory(community_=community)

    request = APIRequestFactory().get("/", {"deprecated": True})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl3.package.name
    assert response.data["results"][1]["name"] == pl1.package.name
    assert response.data["results"][2]["name"] == pl2.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_request_matches_lots_of_packages__paginates_results(
    community: Community,
) -> None:
    for _ in range(21):
        PackageListingFactory(community_=community)

    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 21
    assert response.data["previous"] is None
    assert response.data["next"] is not None
    assert len(response.data["results"]) == 20

    request = APIRequestFactory().get("/", {"page": 2})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 21
    assert response.data["previous"] is not None
    assert response.data["next"] is None
    assert len(response.data["results"]) == 1


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested_page_is_out_of_bounds__returns_error() -> None:
    request = APIRequestFactory().get("/")
    response = BasePackageListApiView().dispatch(request)

    # Requesting empty first page shouldn't cause error.
    assert response.data["count"] == 0
    assert len(response.data["results"]) == 0

    request = APIRequestFactory().get("/", {"page": 2})
    response = BasePackageListApiView().dispatch(request)

    # Error not serialized by dispatch so cast to str manually.
    assert "detail" in response.data
    assert "Page index error" in str(response.data["detail"])


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_multiple_pages_of_results__page_urls_retain_paramaters(
    community: Community,
) -> None:
    cat = PackageCategory.objects.create(name="c", slug="c", community=community)

    for _ in range(41):
        PackageListingFactory(community_=community, categories=[cat])

    request = APIRequestFactory().get(
        "/",
        data={
            "deprecated": True,
            "included_categories": [cat.id],
            "ordering": "most-downloaded",
            "page": 2,
            "q": "test",
        },
    )
    response = BasePackageListApiView().dispatch(request)

    assert response.data["previous"].endswith(
        f"?deprecated=True&included_categories={cat.id}&nsfw=False&ordering=most-downloaded&page=1&q=test",
    )
    assert response.data["next"].endswith(
        f"?deprecated=True&included_categories={cat.id}&nsfw=False&ordering=most-downloaded&page=3&q=test",
    )


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__caches_results(community: Community) -> None:
    pl1 = PackageListingFactory(
        community_=community,
        package_kwargs={"name": "foo"},
    )

    request = APIRequestFactory().get("/", {"ordering": "newest"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "foo"

    pl1.package.name = "bar"
    pl1.package.save()
    PackageListingFactory(community_=community)

    request = APIRequestFactory().get("/", {"ordering": "newest"})
    response = BasePackageListApiView().dispatch(request)

    # Cached result, no changes.
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "foo"

    invalidate_cache(CacheBustCondition.any_package_updated)
    request = APIRequestFactory().get("/", {"ordering": "newest"})
    response = BasePackageListApiView().dispatch(request)

    assert response.data["count"] == 2
    assert response.data["results"][1]["name"] == "bar"


#############################
# CommunityPackageListApiView
#############################


@pytest.mark.django_db
def test_community_view__returns_only_packages_listed_in_community(
    api_client: APIClient,
) -> None:
    expected = PackageListingFactory()
    PackageListingFactory()

    response = api_client.get(
        f"/api/cyberstorm/package/{expected.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["name"] == expected.package.name


@pytest.mark.django_db
def test_community_view__when_package_listed_in_multiple_communities__returns_only_one(
    api_client: APIClient,
) -> None:
    pl1 = PackageListingFactory()
    pl2 = PackageListingFactory(package_=pl1.package)

    response = api_client.get(
        f"/api/cyberstorm/package/{pl1.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["community_identifier"] == pl1.community.identifier

    response = api_client.get(
        f"/api/cyberstorm/package/{pl2.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["community_identifier"] == pl2.community.identifier


@pytest.mark.django_db
def test_community_view__does_not_return_rejected_packages(
    api_client: APIClient,
    community: Community,
) -> None:
    unreviewed = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.unreviewed,
    )
    approved = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.approved,
    )
    PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.rejected,
    )

    response = api_client.get(
        f"/api/cyberstorm/package/{community.identifier}/?ordering=newest",
    )
    result = response.json()

    assert result["count"] == 2
    assert result["results"][0]["name"] == approved.package.name
    assert result["results"][1]["name"] == unreviewed.package.name


@pytest.mark.django_db
def test_community_view__when_community_requires_review__returns_only_approved_packages(
    api_client: APIClient,
) -> None:
    community = CommunityFactory(require_package_listing_approval=True)
    approved = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.approved,
    )
    PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.unreviewed,
    )
    PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.rejected,
    )

    response = api_client.get(
        f"/api/cyberstorm/package/{community.identifier}/?ordering=newest",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["name"] == approved.package.name
