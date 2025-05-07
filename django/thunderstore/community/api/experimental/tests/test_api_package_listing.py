import json
from typing import Union

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

    expected_error_content = {
        TestUserTypes.no_user: True,
        TestUserTypes.unauthenticated: True,
        TestUserTypes.regular_user: "User is missing necessary roles or permissions",
        TestUserTypes.deactivated_user: "User has been deactivated",
        TestUserTypes.service_account: "Service accounts are unable to perform this action",
        TestUserTypes.site_admin: None,
        TestUserTypes.superuser: None,
    }

    expected_error: Union[str, bool, None] = expected_error_content[user_type]

    if not expected_error:
        assert response.status_code == 200
        assert response.json()["categories"] == []
    else:
        assert response.status_code == 403
        if isinstance(expected_error, str):
            assert response.json()["non_field_errors"] == expected_error


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
