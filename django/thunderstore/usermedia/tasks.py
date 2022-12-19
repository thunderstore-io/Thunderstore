from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.usermedia.cleanup import cleanup_expired_uploads


@shared_task(queue=CeleryQueues.Default)
def celery_cleanup_expired_uploads():
    cleanup_expired_uploads()
