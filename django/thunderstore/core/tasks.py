from typing import Dict, Optional, Union

import requests
from celery import shared_task


@shared_task
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
