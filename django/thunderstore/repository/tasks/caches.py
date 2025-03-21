from celery import shared_task  # type: ignore

from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.api.experimental.views.package_index import (
    update_api_experimental_package_index,
)
from thunderstore.repository.api.v1.tasks import (
    update_api_v1_caches,
    update_api_v1_chunked_package_caches,
    update_api_v1_chunked_package_caches_lc,
)


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
    name="thunderstore.repository.tasks.update_chunked_package_caches",
    queue=CeleryQueues.BackgroundLongRunning,
    soft_time_limit=60 * 60 * 23,
    time_limit=60 * 60 * 24,
)
def update_chunked_community_package_caches():
    """
    Update chunked package index cache for all communities excluding
    Lethal Company.
    """
    update_api_v1_chunked_package_caches()


@shared_task(
    name="thunderstore.repository.tasks.update_chunked_package_caches_lc",
    queue=CeleryQueues.BackgroundLongRunning,
    soft_time_limit=60 * 60 * 23,
    time_limit=60 * 60 * 24,
)
def update_chunked_community_package_caches_lc():
    """
    Update chunked package index cache for Lethal Company community.
    """
    update_api_v1_chunked_package_caches_lc()
