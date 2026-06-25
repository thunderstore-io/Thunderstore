import json

import pytest
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import PackageListing

# GET lists the review queue; PATCH bulk-updates review status on the same URL.
REVIEW_URL = "/api/cyberstorm/moderation/review/packages/"
QUEUE_URL = REVIEW_URL
BULK_URL = REVIEW_URL


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
def test_review_queue_filters_by_review_status(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.review_status = PackageListingReviewStatus.rejected
    active_package_listing.save()
    active_package_listing.request_review()

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    # Matching status returns the listing.
    response = api_client.get(REVIEW_URL, {"review_status": "rejected"})
    assert response.status_code == 200
    assert response.json()["count"] == 1

    # A different status filters it out.
    response = api_client.get(REVIEW_URL, {"review_status": "approved"})
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_review_queue_exposes_moderation_context(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.rejection_reason = "Looks off"
    active_package_listing.notes = "internal scratchpad"
    active_package_listing.save()
    active_package_listing.request_review()

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    item = api_client.get(REVIEW_URL).json()["results"][0]
    assert item["rejection_reason"] == "Looks off"
    assert item["internal_notes"] == "internal scratchpad"


@pytest.mark.django_db
def test_review_queue_community_filter_and_options(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    community = active_package_listing.community

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    body = api_client.get(REVIEW_URL).json()
    # The queue's communities are offered as filter options, with counts.
    assert {
        "identifier": community.identifier,
        "name": community.name,
        "count": 1,
    } in body["communities"]

    # Filtering by the listing's community returns it; another doesn't.
    assert (
        api_client.get(REVIEW_URL, {"community": community.identifier}).json()["count"]
        == 1
    )
    assert api_client.get(REVIEW_URL, {"community": "nope"}).json()["count"] == 0


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

    response = api_client.patch(
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
def test_review_queue_bulk_unreviewed_busts_listing_cache(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    from thunderstore.repository.views.package._utils import get_package_listing_or_404

    active_package_listing.review_status = PackageListingReviewStatus.approved
    active_package_listing.save()

    namespace = active_package_listing.package.namespace.name
    name = active_package_listing.package.name
    community = active_package_listing.community

    # Prime the cached lookup with the approved status.
    cached = get_package_listing_or_404(
        namespace=namespace, name=name, community=community
    )
    assert cached.review_status == PackageListingReviewStatus.approved

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        BULK_URL,
        data=json.dumps(
            {
                "package_listing_ids": [active_package_listing.pk],
                "status": "unreviewed",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    active_package_listing.refresh_from_db()
    assert active_package_listing.review_status == PackageListingReviewStatus.unreviewed

    # The cached lookup must reflect the new status, not the stale approval.
    refreshed = get_package_listing_or_404(
        namespace=namespace, name=name, community=community
    )
    assert refreshed.review_status == PackageListingReviewStatus.unreviewed


@pytest.mark.django_db
def test_review_queue_bulk_action_rejects_oversized_batch(
    api_client: APIClient,
):
    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        BULK_URL,
        data=json.dumps(
            {
                "package_listing_ids": list(range(1, 102)),
                "status": "approved",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "package_listing_ids" in response.json()


@pytest.mark.django_db
def test_review_queue_bulk_action_forbidden_for_non_moderator(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    active_package_listing.request_review()
    user = TestUserTypes.get_user_by_type(TestUserTypes.regular_user)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
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
