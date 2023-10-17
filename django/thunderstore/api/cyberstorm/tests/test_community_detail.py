import pytest
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import (
    CommunityAggregatedFields,
    CommunitySite,
    PackageCategory,
)


@pytest.mark.django_db
def test_api_cyberstorm_community_detail_success(
    client: APIClient,
    community_site: CommunitySite,
):
    categories = [
        PackageCategory.objects.create(
            name=i,
            slug=i,
            community=community_site.community,
        )
        for i in range(3)
    ]

    PackageListingFactory(
        community_=community_site.community,
        categories=[categories[0]],
        package_version_kwargs={"downloads": 0},
    )
    PackageListingFactory(
        community_=community_site.community,
        categories=[categories[0], categories[1]],
        package_version_kwargs={"downloads": 23},
    )
    PackageListingFactory(
        community_=community_site.community,
        package_version_kwargs={"downloads": 42},
    )
    CommunityAggregatedFields.create_missing()
    community_site.community.refresh_from_db()
    CommunityAggregatedFields.update_for_community(community_site.community)

    response = client.get(
        f"/api/cyberstorm/community/{community_site.community.identifier}/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_data = response.json()

    c = community_site.community

    assert c.name == response_data["name"]
    assert c.identifier == response_data["identifier"]
    assert c.aggregated.download_count == response_data["total_download_count"]
    assert c.aggregated.package_count == response_data["total_package_count"]
    assert c.background_image_url == response_data["background_image_url"]
    assert c.description == response_data["description"]
    assert c.discord_url == response_data["discord_url"]

    # Include all community's categories even if they're currently not
    # in use, so people see they exists.
    assert type(response_data["package_categories"]) == list
    assert len(response_data["package_categories"]) == 3
    slugs = [c["slug"] for c in response_data["package_categories"]]
    assert "0" in slugs
    assert "1" in slugs
    assert "2" in slugs


@pytest.mark.django_db
def test_api_cyberstorm_community_detail_failure(
    client: APIClient,
    community_site: CommunitySite,
):
    response = client.get(
        "/api/cyberstorm/community/bad/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
