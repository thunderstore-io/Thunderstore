from unittest.mock import PropertyMock, patch

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
@pytest.mark.parametrize("visible", (False, True))
def test_package_detail_view_install_with_mod_manager_button_visibility(
    visible: bool,
    client,
    active_package_listing,
    community_site,
) -> None:
    url = active_package_listing.get_absolute_url()
    install_url = active_package_listing.package.latest.install_url

    path = (
        "thunderstore.community.models.package_listing."
        "PackageListing.has_mod_manager_support"
    )
    with patch(path, new_callable=PropertyMock) as mock_has_mod_manager_support:
        mock_has_mod_manager_support.return_value = visible
        response = client.get(url, HTTP_HOST=community_site.site.domain)

    assert (install_url in str(response.content)) == visible


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
