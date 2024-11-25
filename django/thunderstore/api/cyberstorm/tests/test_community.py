import pytest
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import CommunityAggregatedFields, CommunitySite


@pytest.mark.django_db
def test_api_cyberstorm_community_detail_success(
    client: APIClient,
    community_site: CommunitySite,
):
    PackageListingFactory(
        community_=community_site.community,
        package_version_kwargs={"downloads": 0},
    )
    PackageListingFactory(
        community_=community_site.community,
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
    assert c.hero_image_url == response_data["hero_image_url"]
    assert c.cover_image_url == response_data["cover_image_url"]
    assert c.description == response_data["description"]
    assert c.discord_url == response_data["discord_url"]
    assert c.wiki_url == response_data["wiki_url"]


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
