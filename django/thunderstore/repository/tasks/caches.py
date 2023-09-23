from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.api.v1.tasks import update_api_v1_caches


@shared_task(
    name="thunderstore.repository.tasks.update_api_caches",
    queue=CeleryQueues.BackgroundCache,
)
def update_api_caches():
    update_api_v1_caches()
