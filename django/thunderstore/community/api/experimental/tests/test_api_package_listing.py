import json
from typing import Any

import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.cache.enums import CacheBustCondition
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
    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/update/",
        data=json.dumps({"categories": []}),
        content_type="application/json",
    )

    expected_error_content = {
        TestUserTypes.no_user: {"non_field_errors": ["Must be authenticated"]},
        TestUserTypes.unauthenticated: {"non_field_errors": ["Must be authenticated"]},
        TestUserTypes.regular_user: {
            "non_field_errors": ["User is missing necessary roles or permissions"]
        },
        TestUserTypes.deactivated_user: {"detail": PermissionDenied.default_detail},
        TestUserTypes.service_account: {
            "non_field_errors": ["Service accounts are unable to perform this action"]
        },
        TestUserTypes.site_admin: None,
        TestUserTypes.superuser: None,
    }

    expected_error: Any = expected_error_content[user_type]

    if not expected_error:
        assert response.status_code == 200
        assert response.json()["categories"] == []
    else:
        assert response.status_code == 403
        assert response.json() == expected_error


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


@pytest.mark.django_db
def test_api_experimental_package_listing_update_overrides_readme_and_changelog(
    api_client: APIClient,
    active_package_listing: PackageListing,
    team_owner: TeamMember,
    mocker,
):
    assert team_owner.team == active_package_listing.package.owner
    api_client.force_authenticate(user=team_owner.user)

    mocked_invalidate = mocker.patch(
        "thunderstore.community.api.experimental.views.listing.invalidate_cache_on_commit_async"
    )

    readme_markdown = "Override readme"
    changelog_markdown = "Override changelog"

    response = api_client.post(
        f"/api/experimental/package-listing/{active_package_listing.pk}/update/",
        data=json.dumps(
            {
                "categories": [],
                "readme": readme_markdown,
                "changelog": changelog_markdown,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200

    latest = active_package_listing.package.latest
    latest.refresh_from_db()

    assert latest.readme_override == readme_markdown
    assert latest.changelog_override == changelog_markdown

    # Once for readme, once for changelog
    mocked_invalidate.assert_called_with(CacheBustCondition.any_package_updated)
    assert mocked_invalidate.call_count == 2
