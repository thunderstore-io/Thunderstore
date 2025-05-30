from typing import Dict, List, Union
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views.community_list import CommunityPaginator
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models.community import Community, CommunityAggregatedFields
from thunderstore.community.models.community_site import CommunitySite


@pytest.mark.django_db
def test_api_cyberstorm_community_list_get_success(
    client: APIClient,
    community_site: CommunitySite,
    dummy_image,
    dummy_hero_image,
    dummy_cover_image,
):
    community1 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    community2 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
        background_image=dummy_image,
        hero_image=dummy_hero_image,
        cover_image=dummy_cover_image,
    )

    for _ in range(10):
        PackageListingFactory(
            community_=community1,
            package_version_kwargs={"downloads": 10},
        )
        PackageListingFactory(
            community_=community2,
            package_version_kwargs={"downloads": 5},
        )

    for _ in range(10):
        PackageListingFactory(
            community_=community1,
            package_version_kwargs={"downloads": 3},
            package_kwargs={"is_deprecated": True},
        )
        PackageListingFactory(
            community_=community2,
            review_status=PackageListingReviewStatus.rejected,
            package_version_kwargs={"downloads": 5},
        )

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)

    response = client.get(
        "/api/cyberstorm/community/",
        HTTP_HOST=community_site.site.domain,
    )

    assert response.status_code == 200
    results = response.json()["results"]

    for index, c in enumerate((community_site.community, community1, community2)):
        assert results[index]["name"] == c.name
        assert results[index]["identifier"] == c.identifier
        assert results[index]["total_download_count"] == c.aggregated.download_count
        assert results[index]["total_package_count"] == c.aggregated.package_count
        assert results[index]["background_image_url"] == c.background_image_url
        assert results[index]["community_icon_url"] == c.community_icon_url
        assert results[index]["hero_image_url"] == c.hero_image_url
        assert results[index]["cover_image_url"] == c.cover_image_url
        assert results[index]["description"] == c.description
        assert results[index]["discord_url"] == c.discord_url


@pytest.mark.django_db
def test_api_cyberstorm_community_list_get_failure(api_client: APIClient):
    __query_api(api_client, "ordering=bad", response_status_code=400)


@pytest.mark.django_db
def test_api_cyberstorm_community_list_only_listed_communities_are_returned(
    api_client: APIClient,
) -> None:
    CommunityFactory()
    non_listed = CommunityFactory(is_listed=False)

    data = __query_api(api_client)

    assert (
        len(data["results"]) == 2
    )  # There is the test community, that is created in api_client
    assert not (non_listed.identifier in (c["identifier"] for c in data["results"]))


@pytest.mark.django_db
def test_api_cyberstorm_community_list_are_ordered_by_identifier_by_default(
    api_client: APIClient,
    community,
) -> None:
    a = CommunityFactory(identifier="a")
    b = CommunityFactory(identifier="b")
    c = CommunityFactory(identifier="c")

    data = __query_api(api_client)

    __assert_communities(data, [a, b, c, community])


@pytest.mark.django_db
@patch.object(CommunityPaginator, "page_size", 10)
def test_api_cyberstorm_community_list_pagination(
    api_client: APIClient,
) -> None:

    for _ in range(25):
        CommunityFactory()

    total_count = Community.objects.count()
    assert 30 >= total_count > 20

    data = __query_api(api_client)

    assert data["previous"] is None
    assert data["next"].endswith("page=2")
    assert data["count"] == total_count
    assert len(data["results"]) == 10

    data = __query_api(api_client, "page=2")
    assert data["next"].endswith("page=3")
    assert data["previous"] == data["next"].replace("?page=3", "")
    assert data["count"] == total_count
    assert len(data["results"]) == 10

    data = __query_api(api_client, "page=3")
    assert data["previous"].endswith("page=2")
    assert data["next"] is None
    assert data["count"] == total_count
    assert len(data["results"]) == total_count - 20


def __assert_communities(
    data: Dict,
    communities: Union[Community, List[Community]],
) -> None:
    """
    Check that expected communities are found in results
    """
    expected = communities if isinstance(communities, List) else [communities]

    assert len(data["results"]) == len(expected)

    for i, actual in enumerate(data["results"]):
        assert actual["identifier"] == expected[i].identifier


def __query_api(client: APIClient, query: str = "", response_status_code=200) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.community.list",
    )
    response = client.get(f"{url}?{query}")
    assert response.status_code == response_status_code
    return response.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, search_keywords, name, should_match",
    [
        ("repo", ["repo"], "R.E.P.O", True),
        ("repo", None, "R.E.P.O", False),
        ("ror2", ["ror2"], "Risk of Rain 2", True),
        ("ror2", None, "Risk of Rain 2", False),
        ("ror", ["ror"], "Risk of Rain 2", True),
        ("ror", None, "Risk of Rain 2", False),
        ("lethal", ["lethal", "lc", "lethalcompany"], "Lethal Company", True),
        ("lc", ["lethal", "lc", "lethalcompany"], "Lethal Company", True),
        ("lethalcompany", ["lethal", "lc", "lethalcompany"], "Lethal Company", True),
        ("hello", ["lethal", "lc", "lethalcompany"], "Lethal Company", False),
        ("LETHAL", ["lethal", "lc"], "Lethal Company", True),
        ("Lc", ["lethal", "LC"], "Lethal Company", True),
    ],
)
def test_api_cyberstorm_community_search_with_keywords(
    api_client: APIClient,
    query: str,
    search_keywords: List[str],
    name: str,
    should_match: bool,
) -> None:
    CommunityFactory(name=name, search_keywords=search_keywords)
    data = __query_api(api_client, query=f"search={query}")

    if should_match:
        assert data["count"] == 1
        assert data["results"][0]["name"] == name
    else:
        assert data["count"] == 0
        assert data["results"] == []


@pytest.mark.django_db
def test_api_cyberstorm_community_list_get_include_unlisted(
    api_client: APIClient,
) -> None:
    unlisted_community = CommunityFactory(is_listed=False)

    data = __query_api(api_client, "include_unlisted=true")
    assert data["count"] == 2
    assert unlisted_community.identifier in [c["identifier"] for c in data["results"]]

    data = __query_api(api_client)
    assert data["count"] == 1
    assert unlisted_community.identifier not in [
        c["identifier"] for c in data["results"]
    ]
