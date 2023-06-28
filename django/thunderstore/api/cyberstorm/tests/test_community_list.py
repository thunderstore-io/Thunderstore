from typing import Dict, List, Union

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views import CommunityListAPIView
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models.community import Community
from thunderstore.community.models.community_site import CommunitySite


@pytest.mark.django_db
def test_api_cyberstorm_community_list_get_success(
    client: APIClient, community_site: CommunitySite, dummy_image
):

    community1 = CommunityFactory()
    community2 = CommunityFactory(background_image=dummy_image)
    for x in range(10):
        PackageListingFactory(
            community_=community1, package_version_kwargs={"downloads": 10}
        )
        PackageListingFactory(
            community_=community2, package_version_kwargs={"downloads": 5}
        )

    for x in range(10):
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

    response = client.get(
        "/api/cyberstorm/community/",
        HTTP_HOST=community_site.site.domain,
    )

    assert response.status_code == 200
    resp_com_list = response.json()["results"]

    assert resp_com_list[0]["name"] == community_site.community.name
    assert resp_com_list[0]["identifier"] == community_site.community.identifier
    assert resp_com_list[0]["download_count"] == 0
    assert resp_com_list[0]["package_count"] == 0
    assert resp_com_list[0]["background_image_url"] == None
    assert (
        resp_com_list[0]["background_image_url"]
        == community_site.community.background_image_url
    )
    assert resp_com_list[0]["description"] == community_site.community.description
    assert resp_com_list[0]["discord_link"] == community_site.community.discord_url

    assert resp_com_list[1]["name"] == community1.name
    assert resp_com_list[1]["identifier"] == community1.identifier
    assert resp_com_list[1]["download_count"] == 100
    assert resp_com_list[1]["package_count"] == 10
    assert resp_com_list[1]["background_image_url"] == None
    assert resp_com_list[1]["background_image_url"] == community1.background_image_url
    assert resp_com_list[1]["description"] == community1.description
    assert resp_com_list[1]["discord_link"] == community1.discord_url

    assert resp_com_list[2]["name"] == community2.name
    assert resp_com_list[2]["identifier"] == community2.identifier
    assert resp_com_list[2]["download_count"] == 50
    assert resp_com_list[2]["package_count"] == 10
    assert isinstance(resp_com_list[2]["background_image_url"], str)
    assert resp_com_list[2]["background_image_url"] == community2.background_image_url
    assert resp_com_list[2]["description"] == community2.description
    assert resp_com_list[2]["discord_link"] == community2.discord_url


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
    assert not (non_listed.identifier in [c["identifier"] for c in data["results"]])


@pytest.mark.django_db
def test_api_cyberstorm_community_list_are_ordered_by_name_by_default(
    api_client: APIClient, community
) -> None:
    a = CommunityFactory(name="a")
    b = CommunityFactory(name="b")
    c = CommunityFactory(name="c")

    data = __query_api(api_client)

    __assert_communities(data, [a, b, c, community])


@pytest.mark.django_db
def test_api_cyberstorm_community_list_download_counts() -> None:
    view = CommunityListAPIView()

    community1 = CommunityFactory()
    community2 = CommunityFactory()
    for x in range(10):
        PackageListingFactory(
            community_=community1, package_version_kwargs={"downloads": 10}
        )
        PackageListingFactory(
            community_=community2, package_version_kwargs={"downloads": 5}
        )

    communities = view.get_queryset()

    assert communities.get(name=community1.name).downloads == 100
    assert communities.get(name=community2.name).downloads == 50

    for x in range(10):
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

    communities = view.get_queryset()

    assert communities.get(name=community1.name).downloads == 100
    assert communities.get(name=community2.name).downloads == 50


@pytest.mark.django_db
def test_api_cyberstorm_community_list_package_counts() -> None:
    view = CommunityListAPIView()

    community1 = CommunityFactory()
    community2 = CommunityFactory()
    for x in range(10):
        PackageListingFactory(community_=community1)
        PackageListingFactory(community_=community2)

    communities = view.get_queryset()

    assert communities.get(name=community1.name).pkgs == 10
    assert communities.get(name=community2.name).pkgs == 10

    for x in range(7):
        PackageListingFactory(
            community_=community1, package_kwargs={"is_deprecated": True}
        )
        PackageListingFactory(
            community_=community2, review_status=PackageListingReviewStatus.rejected
        )

    for x in range(3):
        PackageListingFactory(
            community_=community1, package_kwargs={"is_deprecated": False}
        )
        PackageListingFactory(
            community_=community2, review_status=PackageListingReviewStatus.approved
        )

    communities = view.get_queryset()

    assert communities.get(name=community1.name).pkgs == 13
    assert communities.get(name=community2.name).pkgs == 13


@pytest.mark.django_db
def test_api_cyberstorm_community_list_pagination(api_client: APIClient) -> None:

    for i in range(55):
        CommunityFactory()

    data = __query_api(api_client)

    assert data["current"] == 1
    assert data["final"] == 3
    assert data["total"] == 56
    assert data["count"] == 20
    assert len(data["results"]) == 20

    data = __query_api(api_client, "page=2")
    assert data["current"] == 2
    assert data["final"] == 3
    assert data["total"] == 56
    assert data["count"] == 20
    assert (
        len(data["results"]) == 20
    )  # There is the test community, that is created in api_client

    data = __query_api(api_client, "page=3")
    assert data["current"] == 3
    assert data["final"] == 3
    assert data["total"] == 56
    assert data["count"] == 16
    assert (
        len(data["results"]) == 16
    )  # There is the test community, that is created in api_client


def __assert_communities(
    data: Dict, communities: Union[Community, List[Community]]
) -> None:
    """
    Check that expected communities, identified by name, are found in results

    Note that by default the communities in the results are ordered by "name".
    """
    expected = communities if isinstance(communities, List) else [communities]

    assert len(data["results"]) == len(expected)

    for i, actual in enumerate(data["results"]):
        assert actual["name"] == expected[i].name


def __query_api(client: APIClient, query: str = "", response_status_code=200) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.communities",
    )
    response = client.get(f"{url}?{query}")
    assert response.status_code == response_status_code
    return response.json()
