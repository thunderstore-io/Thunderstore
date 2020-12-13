import pytest

from thunderstore.repository.api.v1.tasks import update_api_v1_caches


@pytest.mark.django_db
def test_api_v1(client, active_package_listing, community_site):
    update_api_v1_caches()
    response = client.get("/api/v1/package/", HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name

    uuid = result[0]["uuid4"]
    response = client.get(f"/api/v1/package/{uuid}/", HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert response.json() == result[0]
