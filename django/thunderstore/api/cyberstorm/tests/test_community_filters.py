import pytest
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageCategoryFactory
from thunderstore.community.models import Community, PackageListingSection


@pytest.mark.django_db
def test_community_filters_api_view__returns_package_categories(
    api_client: APIClient,
    community: Community,
):
    c1 = PackageCategoryFactory(community=community, hidden=False)
    c2 = PackageCategoryFactory(community=community, hidden=True)

    response = api_client.get(
        f"/api/cyberstorm/community/{community.identifier}/filters/",
    )
    result = response.json()

    assert len(result["package_categories"]) == 2
    # Hidden categories should be included in API response
    by_id = {c["id"]: c for c in result["package_categories"]}
    assert by_id[str(c1.id)]["hidden"] is False
    assert by_id[str(c2.id)]["hidden"] is True


@pytest.mark.django_db
def test_community_filters_api_view__returns_package_listing_sections(
    api_client: APIClient,
    community: Community,
):
    section1 = PackageListingSection.objects.create(
        community=community,
        name="Mods",
        slug="mods",
        priority=3,
    )
    PackageListingSection.objects.create(
        community=community,
        name="Modpacks",
        slug="modpacks",
        priority=2,
        is_listed=False,
    )
    section3 = PackageListingSection.objects.create(
        community=community,
        name="DLC",
        slug="dlc",
        priority=1,
    )

    response = api_client.get(
        f"/api/cyberstorm/community/{community.identifier}/filters/",
    )
    result = response.json()

    # Filter out unlisted, order by priority.
    assert len(result["sections"]) == 2
    assert result["sections"][0]["uuid"] == str(section1.uuid)
    assert result["sections"][0]["slug"] == section1.slug
    assert result["sections"][1]["uuid"] == str(section3.uuid)
    assert result["sections"][1]["slug"] == section3.slug
