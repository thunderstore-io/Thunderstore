import pytest


@pytest.mark.django_db
def test_package_detail_view(client, active_package_listing, community_site):
    package = active_package_listing.package
    response = client.get(
        active_package_listing.get_absolute_url(community_site.community.identifier),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    text_result = response.content.decode("utf-8")
    assert package.name in text_result
    assert package.full_package_name in text_result


@pytest.mark.django_db
def test_package_dependants_view(client, active_package_listing, community_site):
    response = client.get(
        active_package_listing.dependants_url, HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200
