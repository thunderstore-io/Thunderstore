from typing import Dict, Optional, Union

import requests
from celery import shared_task
from django.core.management import call_command

from thunderstore.core.settings import CeleryQueues


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


@shared_task(
    queue=CeleryQueues.BackgroundTask,
    name="thunderstore.core.tasks.celery_cleanup_sessions",
)
def celery_cleanup_sessions():
    call_command("clearsessions")
