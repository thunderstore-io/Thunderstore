from typing import Dict, Optional, Union

import requests
from celery import shared_task

from thunderstore.core.settings import CeleryQueues


@shared_task(queue=CeleryQueues.Default, rate_limit="2/s")
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
