import pytest

from thunderstore.repository.api.experimental.tasks import (
    update_api_experimental_caches,
)


@pytest.mark.django_db
def test_api_experimental(api_client, active_package_listing, community_site):
    update_api_experimental_caches()
    response = api_client.get(
        "/api/experimental/package/", HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["package"]["name"] == active_package_listing.package.name
    assert (
        result[0]["package"]["full_name"]
        == active_package_listing.package.full_package_name
    )
