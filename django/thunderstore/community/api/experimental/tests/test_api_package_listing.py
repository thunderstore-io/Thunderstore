import json

import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.repository.models import TeamMember


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_api_experimental_package_listing_update_user_types(
    api_client: APIClient,
    user_type: str,
    active_package_listing: PackageListing,
):
    user = TestUserTypes.get_user_by_type(user_type)
    if user not in TestUserTypes.fake_users():
        api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/update/",
        data=json.dumps({"categories": []}),
        content_type="application/json",
    )

    expected_results = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: False,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    should_succeed = expected_results[user_type]

    print(response.content)
    if should_succeed:
        assert response.status_code == 200
        assert response.json()["categories"] == []
    else:
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You do not have permission to perform this action."
        )


@pytest.mark.django_db
def test_api_experimental_package_listing_update(
    api_client: APIClient,
    active_package_listing: PackageListing,
    team_owner: TeamMember,
    package_category: PackageCategory,
):
    assert team_owner.team == active_package_listing.package.owner
    assert package_category.community == active_package_listing.community
    assert active_package_listing.categories.count() == 0
    api_client.force_authenticate(user=team_owner.user)
    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/update/",
        data=json.dumps({"categories": [package_category.slug]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["categories"] == [
        {"name": package_category.name, "slug": package_category.slug}
    ]
    assert active_package_listing.categories.count() == 1
    assert package_category in active_package_listing.categories.all()
