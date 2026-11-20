from datetime import datetime
from typing import Literal

from celery import shared_task
from django.utils import timezone
from pydantic import BaseModel

from thunderstore.core.settings import CeleryQueues
from thunderstore.core.utils import safe_delay_on_commit
from thunderstore.ts_analytics.kafka import KafkaTopic, generate_event_id
from thunderstore.ts_analytics.tasks import send_kafka_message

TASK_LOG_PACKAGE_LIKE = "thunderstore.repository.tasks.log_package_like"

LikeAction = Literal["like", "unlike"]


class AnalyticsEventPackageLike(BaseModel):
    id: int
    package_id: int
    action: LikeAction
    timestamp: datetime


@shared_task(
    queue=CeleryQueues.Analytics,
    name=TASK_LOG_PACKAGE_LIKE,
    ignore_result=True,
)
def log_package_like(package_id: int, action: LikeAction, timestamp: str):
    send_kafka_message(
        topic=KafkaTopic.A_PACKAGE_LIKE_V1,
        payload_string=AnalyticsEventPackageLike(
            id=generate_event_id(),
            package_id=package_id,
            action=action,
            timestamp=datetime.fromisoformat(timestamp),
        ).json(),
    )


def enqueue_package_like_event(package_id: int, action: LikeAction) -> None:
    safe_delay_on_commit(
        log_package_like, package_id, action, timezone.now().isoformat()
    )
