import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from thunderstore.community.models import PackageListing
from thunderstore.ts_trending.models import TrendingScore


@pytest.mark.django_db
def test_order_returns_package_names_per_sort(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    TrendingScore.objects.create(
        listing=active_package_listing,
        score=1.5,
        datetime_computed=timezone.now(),
    )
    url = reverse(
        "api:experimental:trending.order",
        kwargs={"community_id": active_package_listing.community.identifier},
    )

    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data == {
        "trending": [active_package_listing.package.full_package_name],
        "new-and-trending": [],
    }
    assert response["Cache-Control"] == "public, max-age=300"
