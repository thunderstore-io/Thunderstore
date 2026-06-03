import logging
from typing import Dict, Optional, Union

import requests
from celery import shared_task

from thunderstore.core.session_cleanup import cleanup_expired_sessions
from thunderstore.core.settings import CeleryQueues

logger = logging.getLogger(__name__)


@shared_task(queue=CeleryQueues.Default)
def celery_post(
    webhook_url: str,
    data: Optional[str] = None,
    headers: Union[Dict, None] = None,
):
    response = requests.post(
        webhook_url,
        data=data,
        headers=headers,
    )
    return {
        "url": response.url,
        "status": response.status_code,
        "reason": response.reason,
        "content": response.text,
    }


@shared_task(queue=CeleryQueues.BackgroundTask)
def celery_cleanup_sessions():
    deleted = cleanup_expired_sessions()
    logger.info(f"Celery Session cleanup job complete. Total deleted: {deleted}")
