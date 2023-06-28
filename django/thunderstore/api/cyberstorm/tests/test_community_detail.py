import pytest
from django.db.models import Count, Sum
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import CommunitySite
from thunderstore.community.models.community import Community


@pytest.mark.django_db
def test_api_cyberstorm_community_detail_success(
    client: APIClient, community_site: CommunitySite
):
    PackageListingFactory(
        community_=community_site.community, package_version_kwargs={"downloads": 0}
    )
    PackageListingFactory(
        community_=community_site.community, package_version_kwargs={"downloads": 23}
    )
    PackageListingFactory(
        community_=community_site.community, package_version_kwargs={"downloads": 42}
    )

    response = client.get(
        f"/api/cyberstorm/community/{community_site.community.identifier}/",
        HTTP_HOST=community_site.site.domain,
    )
    c = Community.objects.annotate(
        pkgs=Count("package_listings", distinct=True),
        downloads=Sum("package_listings__package__versions__downloads", distinct=True),
    ).get(
        identifier=community_site.community.identifier,
    )
    resp_com = response.json()
    assert response.status_code == 200
    assert c.name == resp_com["name"]
    assert c.identifier == resp_com["identifier"]
    assert c.downloads == resp_com["download_count"]
    assert c.pkgs == resp_com["package_count"]
    assert (
        c.background_image_url.url if bool(c.background_image_url) else None
    ) == resp_com["background_image_url"]
    assert c.description == resp_com["description"]
    assert c.discord_url == resp_com["discord_link"]


@pytest.mark.django_db
def test_api_cyberstorm_community_detail_failure(
    client: APIClient, community_site: CommunitySite
):
    response = client.get(
        f"/api/cyberstorm/community/bad/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
