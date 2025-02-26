import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from conftest import UserType
from thunderstore.community.consts import PackageListingReviewStatus
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


@pytest.mark.django_db
@patch(
    "thunderstore.community.models.package_listing.PackageListing.check_update_categories_permission"
)
@patch(
    "thunderstore.community.models.package_listing.PackageListing.can_be_moderated_by_user"
)
def test_update_categories_success(
    mock_can_be_moderated_by_user,
    mock_check_update_categories_permission,
    active_package_listing: PackageListing,
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
):
    mock_check_update_categories_permission.return_value = True
    mock_can_be_moderated_by_user.return_value = True
    api_client.force_authenticate(user=user)

    url = get_update_categories_url(active_package_listing)
    data = json.dumps({"categories": [package_category.slug]})

    expected_response = {
        "categories": [{"name": package_category.name, "slug": package_category.slug}]
    }

    assert active_package_listing.categories.count() == 0

    response = api_client.post(url, data=data, content_type="application/json")

    assert response.status_code == 200
    assert response.json() == expected_response
    assert active_package_listing.categories.count() == 1
    assert package_category in active_package_listing.categories.all()


@pytest.mark.django_db
def test_update_categories_permission_denied(
    active_package_listing: PackageListing,
    api_client: APIClient,
    package_category: PackageCategory,
):
    url = get_update_categories_url(active_package_listing)
    data = json.dumps({"categories": [package_category.slug]})

    expected_response = {"detail": "You do not have permission to perform this action."}
    response = api_client.post(url, data=data, content_type="application/json")

    assert response.status_code == 403
    assert response.json() == expected_response


@patch(
    "thunderstore.community.models.package_listing.PackageListing.can_user_manage_approval_status"
)
@pytest.mark.django_db
def test_reject_package_listing_success(
    mock_can_user_manage_approval_status,
    api_client: APIClient,
    user: UserType,
    active_package_listing: PackageListing,
):
    mock_can_user_manage_approval_status.return_value = True
    api_client.force_authenticate(user=user)
    data = json.dumps(
        {
            "rejection_reason": "Invalid content",
            "internal_notes": "Some internal notes",
        }
    )

    assert active_package_listing.rejection_reason != "Invalid content"
    assert active_package_listing.notes != "Some internal notes"
    assert active_package_listing.review_status != PackageListingReviewStatus.rejected

    url = get_reject_url(active_package_listing)
    response = api_client.post(url, data, content_type="application/json")

    active_package_listing.refresh_from_db()

    assert response.status_code == 200
    assert response.json() == {"message": "Success"}
    assert active_package_listing.rejection_reason == "Invalid content"
    assert active_package_listing.notes == "Some internal notes"
    assert active_package_listing.review_status == PackageListingReviewStatus.rejected


@pytest.mark.django_db
def test_reject_package_listing_permission_denied(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    data = json.dumps(
        {
            "rejection_reason": "Invalid content",
            "internal_notes": "Some internal notes",
        }
    )
    url = get_reject_url(active_package_listing)
    response = api_client.post(url, data, content_type="application/json")
    assert response.status_code == 403


@pytest.mark.django_db
@patch(
    "thunderstore.community.models.package_listing.PackageListing.can_user_manage_approval_status"
)
def test_approve_package_listing_success(
    mock_can_user_manage_approval_status,
    api_client: APIClient,
    user: UserType,
    active_package_listing: PackageListing,
):
    mock_can_user_manage_approval_status.return_value = True
    api_client.force_authenticate(user=user)
    url = get_approve_url(active_package_listing)

    assert active_package_listing.notes != "Some internal notes"
    assert active_package_listing.review_status != PackageListingReviewStatus.approved

    data = json.dumps({"internal_notes": "Some internal notes"})
    response = api_client.post(url, data=data, content_type="application/json")

    active_package_listing.refresh_from_db()

    assert response.status_code == 200
    assert response.json() == {"message": "Success"}
    assert active_package_listing.notes == "Some internal notes"
    assert active_package_listing.review_status == PackageListingReviewStatus.approved


@pytest.mark.django_db
def test_approve_package_listing_permission_denied(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    url = get_approve_url(active_package_listing)
    data = json.dumps({"internal_notes": "Some internal notes"})
    response = api_client.post(url, data=data, content_type="application/json")
    active_package_listing.refresh_from_db()
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url_action", ["update", "approve", "reject"])
def test_get_community_404(
    url_action: str,
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    namespace_id = active_package_listing.package.namespace.name
    package_name = active_package_listing.package.name
    url = (
        f"/api/cyberstorm/listing/invalid_community_id/"
        f"{namespace_id}/{package_name}/{url_action}/"
    )
    data = json.dumps(
        {
            "rejection_reason": "Invalid content",
            "internal_notes": "Some internal notes",
        }
    )
    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
