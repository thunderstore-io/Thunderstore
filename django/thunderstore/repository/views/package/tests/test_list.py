import pytest
from django.test import Client
from django.urls import reverse

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import CommunitySite, PackageListing
from thunderstore.core.types import UserType


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_authenticated, is_superuser, expected_status",
    [
        (False, False, 403),
        (True, False, 403),
        (True, True, 200),
    ],
)
def test_package_review_list_view_access_control(
    client: Client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    user: UserType,
    is_authenticated: bool,
    is_superuser: bool,
    expected_status: int,
):
    active_package_listing.review_status = PackageListingReviewStatus.rejected
    active_package_listing.save()
    active_package_listing.request_review()

    invalidate_cache(cache_bust_condition=CacheBustCondition.any_package_updated)

    if is_superuser:
        user.is_superuser = True
        user.save()

    if is_authenticated:
        client.force_login(user)

    url = reverse("review-queue.packages")
    response = client.get(url, HTTP_HOST=community_site.site.domain)

    assert response.status_code == expected_status

    if expected_status == 200:
        assert active_package_listing.get_full_url().encode("utf-8") in response.content
