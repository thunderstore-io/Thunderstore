import logging

from celery import shared_task

from thunderstore.community.models import Community, CommunityAggregatedFields
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
