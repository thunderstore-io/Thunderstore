import logging

from celery import shared_task

from thunderstore.community.models import (
    Community,
    CommunityAggregatedFields,
    PackageCategory,
    PackageListing,
)
from thunderstore.core.settings import CeleryQueues

logger = logging.getLogger(__name__)


@shared_task(queue=CeleryQueues.BackgroundTask)
def update_community_aggregated_fields() -> None:
    # Create the relation for all Communities, even if they're unlisted,
    # so they have the relation if they do get listed.
    logger.info("Creating CommunityAggregatedFields")
    CommunityAggregatedFields.create_missing()

    logger.info("Updating fields values for listed communities")
    for c in Community.objects.all():
        CommunityAggregatedFields.update_for_community(c)


@shared_task(
    queue=CeleryQueues.BackgroundTask,
    name="thunderstore.community.tasks.detect_and_assign_modpack_category",
)
def detect_and_assign_modpack_category(package_listing_pk: int):
    listing = PackageListing.objects.select_related("package__latest", "community").get(
        pk=package_listing_pk
    )
    latest = listing.package.latest
    community = listing.community

    mod_dependencies_count = (
        PackageListing.objects.filter(
            package_id__in=latest.dependencies.values_list("package_id", flat=True),
            community=community,
        )
        .exclude(categories__slug="libraries")
        .count()
    )

    if mod_dependencies_count > 4:
        modpacks_category = PackageCategory.objects.filter(
            slug="modpacks", community=community
        ).first()
        if not modpacks_category:
            return f"{community.identifier} community has no modpacks category"
        listing.categories.add(modpacks_category)
        return f"Added modpacks category to listing {package_listing_pk}"
