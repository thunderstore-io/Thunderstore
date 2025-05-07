import logging

from celery import group, shared_task  # type: ignore

from thunderstore.community.models import Community
from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.api.experimental.views.package_index import (
    update_api_experimental_package_index,
)
from thunderstore.repository.api.v1.tasks import (
    update_api_v1_caches,
    update_api_v1_chunked_package_cache_for_community,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="thunderstore.repository.tasks.update_api_caches",
    queue=CeleryQueues.BackgroundCache,
)
def update_api_caches():
    update_api_v1_caches()


@shared_task(
    name="thunderstore.repository.tasks.update_experimental_package_index",
    queue=CeleryQueues.BackgroundLongRunning,
    soft_time_limit=60 * 60 * 23,
    time_limit=60 * 60 * 24,
)
def update_experimental_package_index():
    update_api_experimental_package_index()


@shared_task(
    name="thunderstore.repository.tasks.update_single_community_cache",
    queue=CeleryQueues.BackgroundLongRunning,
    expires=60 * 5,
    soft_time_limit=60 * 15,
)
def update_single_community_cache(community_pk: int):
    """Update the package cache for a single community."""

    community = Community.objects.get(pk=community_pk)
    update_api_v1_chunked_package_cache_for_community(community)


@shared_task(
    name="thunderstore.repository.tasks.update_chunked_package_caches",
    queue=CeleryQueues.BackgroundLongRunning,
    soft_time_limit=60 * 60 * 23,
    time_limit=60 * 60 * 24,
)
def update_chunked_community_package_caches():
    """Update the package caches for all communities in parallel."""

    try:
        communities = Community.objects.values_list("pk", flat=True).iterator()

        task_group = group(
            update_single_community_cache.s(community_pk)
            for community_pk in communities
        )

        result = task_group.apply_async()
        return result
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed starting parallel update of community caches. Error: {e}")
