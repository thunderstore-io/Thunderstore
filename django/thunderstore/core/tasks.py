from typing import Dict, Optional, Union

import requests
from celery import shared_task

from thunderstore.core.settings import CeleryQueues


@shared_task(queue=CeleryQueues.Default)
def celery_post(
    webhook_url: str,
    data: Optional[str] = None,
    headers: Union[Dict, None] = None,
) -> None:
    requests.post(
        webhook_url,
        data=data,
        headers=headers,
    )
