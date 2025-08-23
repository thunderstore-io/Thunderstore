from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from thunderstore.api.cyberstorm.views.package_listing_list import (
    BasePackageListAPIView,
)
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListing,
    PackageListingSection,
)
from thunderstore.repository.factories import (
    NamespaceFactory,
    PackageRatingFactory,
    PackageVersionFactory,
)
from thunderstore.repository.models import Team

########################
# BasePackageListAPIView
########################


mock_base_package_list_api_view = patch.multiple(
    BasePackageListAPIView,
    viewname="api:cyberstorm:cyberstorm.listing.by-community-list",
)


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__return_data_structure() -> None:
    pl = PackageListingFactory()
    request = APIRequestFactory().get("/")
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

    expected_results_keys = [
        "categories",
        "community_identifier",
        "description",
        "download_count",
        "icon_url",
        "is_deprecated",
        "is_nsfw",
        "is_pinned",
        "last_updated",
        "name",
        "namespace",
        "rating_count",
        "size",
        "datetime_created",
    ]

    assert response.status_code == 200

    response_results = response.data["results"][0]
    assert expected_results_keys == list(response_results.keys())


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_inactive_packages() -> None:
    pl = PackageListingFactory(package_kwargs={"is_active": False})

    request = APIRequestFactory().get("/")
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_deprecated_packages() -> None:
    pl = PackageListingFactory(package_kwargs={"is_deprecated": True})

    request = APIRequestFactory().get("/")
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__include_deprecated_packages() -> None:
    pl = PackageListingFactory(package_kwargs={"is_deprecated": True})

    request = APIRequestFactory().get("/", {"deprecated": True})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

    assert response.data["count"] == 1


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__by_default__filters_out_nsfw() -> None:
    pl = PackageListingFactory(has_nsfw_content=True)

    request = APIRequestFactory().get("/")
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

    assert response.data["count"] == 0


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested__include_nsfw_packages() -> None:
    pl = PackageListingFactory(has_nsfw_content=True)

    request = APIRequestFactory().get("/", {"nsfw": True})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=pl.community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 2


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_including_category__filters_out_not_matched(
    community: Community,
) -> None:
    cat = PackageCategory.objects.create(name="c", slug="c", community=community)
    PackageListingFactory(community_=community, categories=[])
    included = PackageListingFactory(community_=community, categories=[cat])

    request = APIRequestFactory().get("/", {"included_categories": [str(cat.id)]})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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

    request = APIRequestFactory().get("/", {"excluded_categories": [str(cat.id)]})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=expected.community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == pl1.package.name

    request = APIRequestFactory().get("/", {"q": pl2.package.owner.name})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == pl2.package.name

    request = APIRequestFactory().get("/", {"q": pl3.package.latest.description})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 3
    assert response.data["results"][0]["name"] == pl3.package.name
    assert response.data["results"][1]["name"] == pl2.package.name
    assert response.data["results"][2]["name"] == pl1.package.name

    # Downloads of all versions are counted towards package's downloads.
    PackageVersionFactory(package=pl1.package, downloads=9001, version_number="1.0.1")

    request = APIRequestFactory().get("/", {"ordering": "most-downloaded"})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

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
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 21
    assert response.data["previous"] is None
    assert response.data["next"] is not None
    assert len(response.data["results"]) == 20

    request = APIRequestFactory().get("/", {"page": 2})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["count"] == 21
    assert response.data["previous"] is not None
    assert response.data["next"] is None
    assert len(response.data["results"]) == 1


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_base_view__when_requested_page_is_out_of_bounds__returns_error(
    community: Community,
) -> None:
    request = APIRequestFactory().get("/")
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    # Requesting empty first page shouldn't cause error.
    assert response.data["count"] == 0
    assert len(response.data["results"]) == 0

    request = APIRequestFactory().get("/", {"page": 2})
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    # Error not serialized by dispatch so cast to str manually.
    assert "detail" in response.data
    assert "Invalid page" in str(response.data["detail"])


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
            "included_categories": [str(cat.id)],
            "ordering": "most-downloaded",
            "page": 2,
            "q": "test",
        },
    )
    response = BasePackageListAPIView().dispatch(
        request,
        community_id=community.identifier,
    )

    assert response.data["previous"].endswith(
        f"?deprecated=True&included_categories={cat.id}&nsfw=False&ordering=most-downloaded&page=1&q=test",
    )
    assert response.data["next"].endswith(
        f"?deprecated=True&included_categories={cat.id}&nsfw=False&ordering=most-downloaded&page=3&q=test",
    )


######################################
# PackageListingByCommunityListAPIView
######################################


@pytest.mark.django_db
def test_listing_by_community_view__returns_only_packages_listed_in_community(
    api_client: APIClient,
) -> None:
    expected = PackageListingFactory()
    PackageListingFactory()

    response = api_client.get(
        f"/api/cyberstorm/listing/{expected.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["name"] == expected.package.name


@pytest.mark.django_db
def test_listing_by_community_view__when_package_listed_in_multiple_communities__returns_only_one(
    api_client: APIClient,
) -> None:
    pl1 = PackageListingFactory()
    pl2 = PackageListingFactory(package_=pl1.package)

    response = api_client.get(
        f"/api/cyberstorm/listing/{pl1.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["community_identifier"] == pl1.community.identifier

    response = api_client.get(
        f"/api/cyberstorm/listing/{pl2.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["community_identifier"] == pl2.community.identifier


@pytest.mark.django_db
def test_listing_by_community_view__when_package_listed_in_multiple_communities__returns_correct_community_info(
    api_client: APIClient,
) -> None:
    com1pack1 = PackageListingFactory()
    com2pack1 = PackageListingFactory(package_=com1pack1.package)
    com1pack2 = PackageListingFactory(community_=com1pack1.community)
    com2pack2 = PackageListingFactory(
        community_=com2pack1.community,
        package_=com1pack2.package,
    )

    response = api_client.get(
        f"/api/cyberstorm/listing/{com1pack2.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert (
        result["results"][0]["community_identifier"] == com1pack2.community.identifier
    )
    assert (
        result["results"][1]["community_identifier"] == com1pack2.community.identifier
    )

    response = api_client.get(
        f"/api/cyberstorm/listing/{com2pack2.community.identifier}/",
    )
    result = response.json()

    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert (
        result["results"][0]["community_identifier"] == com2pack2.community.identifier
    )
    assert (
        result["results"][1]["community_identifier"] == com2pack2.community.identifier
    )


@pytest.mark.django_db
def test_listing_by_community_view__does_not_return_rejected_packages(
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
        f"/api/cyberstorm/listing/{community.identifier}/?ordering=newest",
    )
    result = response.json()

    assert result["count"] == 2
    assert result["results"][0]["name"] == approved.package.name
    assert result["results"][1]["name"] == unreviewed.package.name


@pytest.mark.django_db
def test_listing_by_community__does_not_return_rejected_multi_community_packages(
    api_client: APIClient,
    active_package,
) -> None:
    """
    Ensure that a package listed in multiple communities, but rejected in one of them,
    does not appear in the listing of the community where it has been rejected.
    """

    community1 = CommunityFactory()
    community2 = CommunityFactory()

    PackageListingFactory(
        community_=community1,
        package_=active_package,
        review_status=PackageListingReviewStatus.approved,
    )

    PackageListingFactory(
        community_=community2,
        package_=active_package,
        review_status=PackageListingReviewStatus.rejected,
    )

    # Should return one package since it is approved in community1
    url = f"/api/cyberstorm/listing/{community1.identifier}/"
    response = api_client.get(url)
    assert response.json()["count"] == 1

    # Should return zero packages since it is rejected in community2
    url = f"/api/cyberstorm/listing/{community2.identifier}/"
    response = api_client.get(url)
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_listing_by_community_view__when_community_requires_review__returns_only_approved_packages(
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
        f"/api/cyberstorm/listing/{community.identifier}/?ordering=newest",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["name"] == approved.package.name


######################################
# PackageListingByNamespaceListAPIView
######################################


@pytest.mark.django_db
def test_listing_by_namespace_view__returns_only_packages_listed_in_community_belonging_to_namespace(
    api_client: APIClient,
    community: Community,
    team: Team,
) -> None:
    namespace = team.get_namespace()
    expected = PackageListingFactory(
        community_=community,
        package_kwargs={"namespace": namespace},
    )
    PackageListingFactory(community_=community)
    PackageListingFactory(package_kwargs={"namespace": namespace})

    response = api_client.get(
        f"/api/cyberstorm/listing/{community.identifier}/{namespace.name}/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["name"] == expected.package.name


##############################
# PackageDependantsListAPIView
##############################


@pytest.mark.django_db
def test_listing_by_dependency_view__returns_only_dependants_of_requested_package(
    api_client: APIClient,
    community: Community,
) -> None:
    # Target dependency,
    package = "Mod"
    target_ns = NamespaceFactory()
    target_dependency = PackageListingFactory(
        community_=community,
        package_kwargs={"name": package, "namespace": target_ns},
    )

    # Target package depends on target dependency.
    target_package = PackageListingFactory(community_=community)
    target_package.package.latest.dependencies.set(
        [target_dependency.package.latest.id],
    )

    # Other dependency is listed in the same community and has the same
    # name as the target dependency, but belongs to a different
    # namespace.
    other_ns = NamespaceFactory()
    other_dependency = PackageListingFactory(
        community_=community,
        package_kwargs={"name": package, "namespace": other_ns},
    )
    other_package = PackageListingFactory(community_=community)
    other_package.package.latest.dependencies.set([other_dependency.package.latest.id])

    response = api_client.get(
        f"/api/cyberstorm/listing/{community.identifier}/{target_ns.name}/{package}/dependants/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["namespace"] == target_package.package.namespace.name
    assert result["results"][0]["name"] == target_package.package.name


@pytest.mark.django_db
def test_listing_by_dependency_view__returns_only_packages_listed_in_community(
    api_client: APIClient,
    community: Community,
) -> None:
    dependency_listing = PackageListingFactory(community_=community)
    dependency_id = dependency_listing.package.latest.id
    expected = PackageListingFactory(community_=community)
    expected.package.latest.dependencies.set([dependency_id])
    other_community_listing = PackageListingFactory()
    other_community_listing.package.latest.dependencies.set([dependency_id])

    response = api_client.get(
        f"/api/cyberstorm/listing/{community.identifier}/{dependency_listing.package.namespace.name}/{dependency_listing.package.name}/dependants/",
    )
    result = response.json()

    assert result["count"] == 1
    assert result["results"][0]["namespace"] == expected.package.namespace.name
    assert result["results"][0]["name"] == expected.package.name


@mock_base_package_list_api_view
@pytest.mark.django_db
def test_annotate_queryset__adds_annotation_fields() -> None:
    PackageListingFactory()
    view = BasePackageListAPIView()
    qs = PackageListing.objects.all()
    annotated_qs = view._annotate_queryset(qs)

    assert "download_count" in annotated_qs.query.annotations
    assert "rating_count" in annotated_qs.query.annotations


@pytest.mark.django_db
def test_annotate_queryset__returns_correct_values() -> None:
    listing = PackageListingFactory()
    package = listing.package
    package.latest.downloads = 10
    package.latest.save()

    PackageVersionFactory(package=package, downloads=20, version_number="1.0.1")

    PackageRatingFactory(package=package)
    PackageRatingFactory(package=package)

    view = BasePackageListAPIView()
    annotated_qs = view._annotate_queryset(PackageListing.objects.filter(id=listing.id))
    annotated = annotated_qs.first()

    assert annotated.download_count == 30
    assert annotated.rating_count == 2
