from datetime import datetime
from typing import Dict, List, Tuple, Type, Union

from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Concat

from thunderstore.community.models import Community, PackageListing
from thunderstore.ts_trending.exceptions import EmptyScoresError, StaleScoresError
from thunderstore.ts_trending.models import NewAndTrendingScore, TrendingScore

PackageScore = Tuple[int, float]
ScoresByCommunity = Dict[str, List[PackageScore]]
ScoresBySort = Dict[str, ScoresByCommunity]

SORT_MODELS: Dict[str, Union[Type[TrendingScore], Type[NewAndTrendingScore]]] = {
    "trending": TrendingScore,
    "new-and-trending": NewAndTrendingScore,
}


@transaction.atomic
def replace_scores(computed_at: datetime, sorts: ScoresBySort) -> Dict[str, int]:
    """
    Replace the stored scores of every trending sort variant.

    Scores are grouped by sort and then by community identifier as
    (package_id, score) pairs. Pairs without a matching listing are
    dropped.

    Returns the number of scores stored per sort variant.
    """
    for model in SORT_MODELS.values():
        if model.objects.filter(datetime_computed__gte=computed_at).exists():
            raise StaleScoresError("Stored scores are as recent or newer")

    identifiers = {x for communities in sorts.values() for x in communities}
    listing_ids = {
        (identifier, package_id): listing_id
        for identifier, package_id, listing_id in PackageListing.objects.filter(
            community__identifier__in=identifiers
        ).values_list("community__identifier", "package_id", "pk")
    }

    listing_scores = {
        sort: _get_listing_scores(sorts[sort], listing_ids) for sort in SORT_MODELS
    }
    if not any(listing_scores.values()):
        raise EmptyScoresError("No scores match a listing")

    for sort, model in SORT_MODELS.items():
        model.objects.all().delete()
        model.objects.bulk_create(
            [
                model(listing_id=listing_id, score=score, datetime_computed=computed_at)
                for listing_id, score in listing_scores[sort].items()
            ]
        )

    return {sort: len(scores) for sort, scores in listing_scores.items()}


def get_package_order(community: Community) -> Dict[str, List[str]]:
    """
    Get the full package names of a community's scored listings for every
    trending sort variant in descending order.
    """
    listings = (
        PackageListing.objects.active()
        .filter_by_community_approval_rule()
        .filter(community=community)
    )

    full_package_name = Concat(
        "listing__package__owner__name",
        Value("-"),
        "listing__package__name",
    )

    order = {}
    for sort, model in SORT_MODELS.items():
        scores = model.objects.filter(listing__in=listings).order_by(
            "-score",
            "-listing__package__date_updated",
            "-listing__package__pk",
        )
        order[sort] = list(scores.values_list(full_package_name, flat=True))

    return order


def _get_listing_scores(
    scores: ScoresByCommunity,
    listing_ids: Dict[Tuple[str, int], int],
) -> Dict[int, float]:
    listing_scores = {}
    for identifier, pairs in scores.items():
        for package_id, score in pairs:
            listing_id = listing_ids.get((identifier, package_id))
            if listing_id is not None:
                listing_scores[listing_id] = score

    return listing_scores
