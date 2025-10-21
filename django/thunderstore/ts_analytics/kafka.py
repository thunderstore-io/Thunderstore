import json
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, Optional, Union

from celery import shared_task
from confluent_kafka import Producer
from django.conf import settings

from thunderstore.core.settings import CeleryQueues


class KafkaTopic(str, Enum):
    PACKAGE_DOWNLOADED = "ts.package.downloaded"
    PACKAGE_UPDATED = "ts.package.updated"
    PACKAGE_VERSION_UPDATED = "ts.package.version.updated"
    PACKAGE_LISTING_UPDATED = "ts.package.listing.updated"
    COMMUNITY_UPDATED = "ts.community.updated"


def send_kafka_message(
    topic: Union[KafkaTopic, str], payload: dict, key: Optional[str] = None
):
    client = get_kafka_client()
    client.send(topic=topic, payload=payload, key=key)


@shared_task(
    queue=CeleryQueues.Analytics,
    name="thunderstore.analytics.send_kafka_message_async",
    ignore_result=True,
)
def send_kafka_message_async(
    topic: Union[KafkaTopic, str], payload: dict, key: Optional[str] = None
):
    send_kafka_message(topic=topic, payload=payload, key=key)


class KafkaClient:
    def __init__(self, config: Dict[str, Any]):
        self._producer = Producer(config)

    def send(
        self,
        topic: Union[KafkaTopic, str],
        payload: dict,
        key: Optional[str] = None,
    ):
        value_bytes = json.dumps(payload).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        topic_str = topic.value if isinstance(topic, KafkaTopic) else topic
        self._producer.produce(
            topic=topic_str,
            value=value_bytes,
            key=key_bytes,
        )

        self._producer.poll(0)


class DummyKafkaClient:
    """A dummy Kafka client that does nothing when Kafka is disabled."""

    def send(
        self, topic: Union[KafkaTopic, str], payload: dict, key: Optional[str] = None
    ):
        pass


@lru_cache(maxsize=1)
def get_kafka_client() -> Union[KafkaClient, DummyKafkaClient]:
    # Return dummy client if Kafka is disabled
    if not getattr(settings, "KAFKA_ENABLED", False):
        return DummyKafkaClient()

    config = getattr(settings, "KAFKA_CONFIG", None)
    if not config:
        raise RuntimeError("KAFKA_CONFIG is not configured.")

    if not config.get("bootstrap.servers"):
        raise RuntimeError("Kafka bootstrap servers are not configured.")

    return KafkaClient(config)
