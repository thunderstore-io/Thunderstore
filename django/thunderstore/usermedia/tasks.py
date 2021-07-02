from celery import shared_task

from thunderstore.usermedia.cleanup import cleanup_expired_uploads


@shared_task
def celery_cleanup_expired_uploads():
    cleanup_expired_uploads()
