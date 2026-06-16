import json

import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import PackageListing

QUEUE_URL = "/api/cyberstorm/moderation/review-queue/packages/"
BULK_URL = "/api/cyberstorm/moderation/review-queue/packages/bulk-action/"


@pytest.mark.django_db
def test_review_queue_requires_authentication(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    response = api_client.get(QUEUE_URL)
    assert response.status_code == 401


@pytest.mark.django_db
def test_review_queue_forbidden_for_non_moderator(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    user = TestUserTypes.get_user_by_type(TestUserTypes.regular_user)
    api_client.force_authenticate(user=user)

    response = api_client.get(QUEUE_URL)
    assert response.status_code == 403


@pytest.mark.django_db
def test_review_queue_lists_requested_packages_for_moderator(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.review_status = PackageListingReviewStatus.rejected
    active_package_listing.save()
    active_package_listing.request_review()

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.get(QUEUE_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    item = body["results"][0]
    # Surfaces a rejected listing (hidden by the public endpoints).
    assert item["name"] == active_package_listing.package.name
    assert item["review_status"] == "rejected"
    assert item["is_review_requested"] is True


@pytest.mark.django_db
def test_review_queue_excludes_non_requested(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.get(QUEUE_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_review_queue_bulk_approve(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        BULK_URL,
        data=json.dumps(
            {
                "package_listing_ids": [active_package_listing.pk],
                "status": "approved",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    assert response.json()["updated"] == 1
    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.approved
    assert active_package_listing.is_review_requested is False


@pytest.mark.django_db
def test_review_queue_bulk_request_review(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        BULK_URL,
        data=json.dumps(
            {
                "package_listing_ids": [active_package_listing.pk],
                "status": "review-queue",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    active_package_listing.refresh_from_db()
    assert active_package_listing.is_review_requested is True


@pytest.mark.django_db
def test_review_queue_bulk_action_forbidden_for_non_moderator(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    user = TestUserTypes.get_user_by_type(TestUserTypes.regular_user)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        BULK_URL,
        data=json.dumps(
            {
                "package_listing_ids": [active_package_listing.pk],
                "status": "approved",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 403
    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status != PackageListingReviewStatus.approved
