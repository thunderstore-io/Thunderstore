from datetime import timedelta

import pytest
from django.utils import timezone

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import Community, PackageListing
from thunderstore.ts_trending.exceptions import StaleScoresError
from thunderstore.ts_trending.models import NewAndTrendingScore, TrendingScore
from thunderstore.ts_trending.services.score import get_package_order, replace_scores


@pytest.mark.django_db
def test_replace_scores_maps_package_ids_to_listings(community: Community) -> None:
    listing = PackageListingFactory(community_=community)
    previously_scored = PackageListingFactory(community_=community)
    elsewhere = PackageListingFactory()
    now = timezone.now()
    TrendingScore.objects.create(
        listing=previously_scored,
        score=9.5,
        datetime_computed=now - timedelta(hours=6),
    )

    stored = replace_scores(
        computed_at=now,
        sorts={
            "trending": {
                community.identifier: [
                    (listing.package.pk, 3.5),
                    (elsewhere.package.pk, 2.5),
                ],
                "unknown": [(listing.package.pk, 1.5)],
            },
            "new-and-trending": {
                community.identifier: [(listing.package.pk, 0.5)],
            },
        },
    )

    assert stored == {"trending": 1, "new-and-trending": 1}
    trending = TrendingScore.objects.get()
    assert trending.listing == listing
    assert trending.score == 3.5
    assert trending.datetime_computed == now
    assert NewAndTrendingScore.objects.get().listing == listing


@pytest.mark.django_db
def test_replace_scores_rejects_stale_scores(
    active_package_listing: PackageListing,
) -> None:
    now = timezone.now()
    NewAndTrendingScore.objects.create(
        listing=active_package_listing,
        score=1.5,
        datetime_computed=now,
    )

    with pytest.raises(StaleScoresError):
        replace_scores(
            computed_at=now,
            sorts={"trending": {}, "new-and-trending": {}},
        )

    assert NewAndTrendingScore.objects.count() == 1


@pytest.mark.django_db
def test_get_package_order_lists_names_by_score(community: Community) -> None:
    low = PackageListingFactory(community_=community)
    high = PackageListingFactory(community_=community)
    PackageListingFactory(community_=community)
    elsewhere = PackageListingFactory()
    now = timezone.now()
    TrendingScore.objects.create(listing=low, score=1.5, datetime_computed=now)
    TrendingScore.objects.create(listing=high, score=3.5, datetime_computed=now)
    TrendingScore.objects.create(listing=elsewhere, score=9.5, datetime_computed=now)
    NewAndTrendingScore.objects.create(listing=low, score=0.5, datetime_computed=now)

    order = get_package_order(community)

    assert order == {
        "trending": [
            high.package.full_package_name,
            low.package.full_package_name,
        ],
        "new-and-trending": [low.package.full_package_name],
    }


@pytest.mark.django_db
def test_get_package_order_omits_hidden_listings(community: Community) -> None:
    community.require_package_listing_approval = True
    community.save()
    visible = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.approved,
    )
    hidden = [
        PackageListingFactory(
            community_=community,
            review_status=PackageListingReviewStatus.unreviewed,
        ),
        PackageListingFactory(
            community_=community,
            review_status=PackageListingReviewStatus.rejected,
        ),
        PackageListingFactory(
            community_=community,
            review_status=PackageListingReviewStatus.approved,
            package_kwargs={"is_active": False},
        ),
    ]
    now = timezone.now()
    for listing in [visible, *hidden]:
        TrendingScore.objects.create(listing=listing, score=1.5, datetime_computed=now)

    order = get_package_order(community)

    assert order["trending"] == [visible.package.full_package_name]
