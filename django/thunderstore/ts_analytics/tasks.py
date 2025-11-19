from typing import Optional

from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.ts_analytics.kafka import get_kafka_client

TASK_SEND_KAFKA_MESSAGE = "thunderstore.ts_analytics.tasks.send_kafka_message"


@shared_task(
    queue=CeleryQueues.Analytics,
    name="thunderstore.analytics.send_kafka_message",
    ignore_result=True,
)
def send_kafka_message(topic: str, payload_string: str, key: Optional[str] = None):
    client = get_kafka_client()
    client.send(topic=topic, payload_string=payload_string, key=key)
