import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_package_detail_view(client, active_package_listing, community_site):
    package = active_package_listing.package
    response = client.get(
        active_package_listing.get_absolute_url(), HTTP_HOST=community_site.site.domain
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


@pytest.mark.django_db
def test_community_list_view(client, community_site):
    response = client.get(
        reverse("communities"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    data = response.content.decode()
    assert community_site.community.name in data
    assert community_site.community.full_url in data
