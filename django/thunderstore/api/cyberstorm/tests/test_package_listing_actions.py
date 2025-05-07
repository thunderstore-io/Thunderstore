import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes, UserType
from thunderstore.community.models import PackageCategory, PackageListing


def get_base_url(package_listing):
    namespace_id = package_listing.package.namespace.name
    package_name = package_listing.package.name
    community_id = package_listing.community.identifier
    return f"/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}"


def get_update_categories_url(package_listing):
    return f"{get_base_url(package_listing)}/update/"


def get_approve_url(package_listing):
    return f"{get_base_url(package_listing)}/approve/"


def get_reject_url(package_listing):
    return f"{get_base_url(package_listing)}/reject/"


def perform_404_test(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
    url: str,
):
    active_package_listing.package.owner.add_member(user, role="owner")
    api_client.force_authenticate(user=user)

    data = json.dumps(
        {
            "rejection_reason": "Invalid content",
            "internal_notes": "Some internal notes",
        }
    )

    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


def perform_package_listing_action_test(
    api_client: APIClient,
    package_listing: PackageListing,
    user_type: str,
    url: str,
    data: dict,
):
    user = TestUserTypes.get_user_by_type(user_type)

    is_fake_user = user in TestUserTypes.fake_users()
    is_unauthenticated = user_type == TestUserTypes.unauthenticated

    if not is_fake_user and not is_unauthenticated:
        api_client.force_authenticate(user=user)

    data = json.dumps(data)
    response = api_client.post(url, data=data, content_type="application/json")

    package_listing.refresh_from_db()

    expected_status_code = {
        TestUserTypes.no_user: 401,
        TestUserTypes.unauthenticated: 401,
        TestUserTypes.regular_user: 403,
        TestUserTypes.deactivated_user: 403,
        TestUserTypes.service_account: 403,
        TestUserTypes.site_admin: 200,
        TestUserTypes.superuser: 200,
    }

    assert response.status_code == expected_status_code[user_type]


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_update_categories_success(
    active_package_listing: PackageListing,
    api_client: APIClient,
    package_category: PackageCategory,
    user_type: str,
):

    perform_package_listing_action_test(
        api_client=api_client,
        package_listing=active_package_listing,
        user_type=user_type,
        url=get_update_categories_url(active_package_listing),
        data={"categories": [package_category.slug]},
    )


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_reject_package_listing(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user_type: str,
):

    perform_package_listing_action_test(
        api_client=api_client,
        package_listing=active_package_listing,
        user_type=user_type,
        url=get_reject_url(active_package_listing),
        data={"rejection_reason": "Invalid content"},
    )


@pytest.mark.django_db
def test_reject_package_listing_required_fields(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    user = TestUserTypes.get_user_by_type(TestUserTypes.site_admin)
    api_client.force_authenticate(user=user)

    url = get_reject_url(active_package_listing)
    response = api_client.post(
        url, data=json.dumps({}), content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json() == {"rejection_reason": ["This field is required."]}


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_approve_package_listing(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user_type: str,
):
    perform_package_listing_action_test(
        api_client=api_client,
        package_listing=active_package_listing,
        user_type=user_type,
        url=get_approve_url(active_package_listing),
        data={},
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_action", ["update", "approve", "reject"])
def test_get_community_404(
    url_action: str,
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
):
    url = (
        f"/api/cyberstorm/listing/invalid_community_id/"
        f"{active_package_listing.package.namespace.name}/"
        f"{active_package_listing.package.name}/{url_action}/"
    )

    perform_404_test(
        api_client=api_client,
        active_package_listing=active_package_listing,
        user=user,
        url=url,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_action", ["update", "approve", "reject"])
def test_get_package_404(
    url_action: str,
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
):
    url = (
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/"
        f"{active_package_listing.package.namespace.name}/"
        f"invalid_package_name/{url_action}/"
    )

    perform_404_test(
        api_client=api_client,
        active_package_listing=active_package_listing,
        user=user,
        url=url,
    )


@pytest.mark.django_db
@patch(
    "thunderstore.community.models.package_listing.PackageListing.can_user_manage_approval_status"
)
def test_reject_package_listing_permission_error(
    mock_can_user_manage_approval_status,
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that PermissionError is re-raised as PermissionDenied"""

    mock_can_user_manage_approval_status.return_value = False

    user = TestUserTypes.get_user_by_type(TestUserTypes.site_admin)
    api_client.force_authenticate(user=user)

    url = get_reject_url(active_package_listing)
    data = json.dumps(
        {
            "rejection_reason": "Invalid content",
            "internal_notes": "Some internal notes",
        }
    )

    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == 403
