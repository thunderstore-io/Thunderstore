from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.api.experimental.views.package_index import (
    update_api_experimental_package_index,
)
from thunderstore.repository.api.v1.tasks import update_api_v1_caches


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
