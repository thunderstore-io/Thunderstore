import json
from enum import Enum
from typing import Any, Dict, Optional, Union

from celery import shared_task
from confluent_kafka import Producer
from django.conf import settings
from django.db import transaction

from thunderstore.core.settings import CeleryQueues


class KafkaTopic(str, Enum):
    PACKAGE_DOWNLOADED = "ts.package.downloaded"
    PACKAGE_UPDATED = "ts.package.updated"
    PACKAGE_VERSION_UPDATED = "ts.package.version.updated"
    PACKAGE_LISTING_UPDATED = "ts.package.listing.updated"
    COMMUNITY_UPDATED = "ts.community.updated"


def send_kafka_message(topic: str, payload: dict, key: Optional[str] = None):
    payload_string = json.dumps(payload)
    transaction.on_commit(
        lambda: send_kafka_message_task.delay(
            topic=topic,
            payload_string=payload_string,
            key=key,
        )
    )


@shared_task(
    queue=CeleryQueues.Analytics,
    name="thunderstore.analytics.send_kafka_message_async",
    ignore_result=True,
)
def send_kafka_message_task(topic: str, payload_string: str, key: Optional[str] = None):
    client = get_kafka_client()
    client.send(topic=topic, payload_string=payload_string, key=key)


class KafkaClient:
    def __init__(self, config: Dict[str, Any]):
        self._producer = Producer(config)

    def close(self):
        """Flushes any remaining messages and closes the producer."""
        # The timeout (e.g., 10 seconds) is the maximum time to wait.
        remaining_messages = self._producer.flush(timeout=10)
        if remaining_messages > 0:
            print(f"WARNING: {remaining_messages} messages still in queue after flush.")

    def send(
        self,
        topic: str,
        payload_string: str,
        key: Optional[str] = None,
    ):
        value_bytes = payload_string.encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        self._producer.produce(
            topic=topic,
            value=value_bytes,
            key=key_bytes,
        )


class ProdKafkaClient(KafkaClient):
    """
    A Kafka client for production environments that prepends 'prod.'
    to all topics before sending.
    """

    def send(
        self,
        topic: str,
        payload_string: str,
        key: Optional[str] = None,
    ):
        prod_topic = f"prod.{topic}"
        super().send(
            topic=prod_topic,
            payload_string=payload_string,
            key=key,
        )


class DevKafkaClient(KafkaClient):
    """
    A Kafka client for development environments that prepends 'dev.'
    to all topics before sending.
    """

    def send(
        self,
        topic: str,
        payload_string: str,
        key: Optional[str] = None,
    ):
        dev_topic = f"dev.{topic}"
        super().send(
            topic=dev_topic,
            payload_string=payload_string,
            key=key,
        )


class DummyKafkaClient:
    """A dummy Kafka client that does nothing when Kafka is disabled."""

    def send(self, topic: str, payload_string: str, key: Optional[str] = None):
        pass


_KAFKA_CLIENT_INSTANCE = None


def get_kafka_client() -> Union[KafkaClient, DevKafkaClient, DummyKafkaClient]:
    global _KAFKA_CLIENT_INSTANCE

    if _KAFKA_CLIENT_INSTANCE is not None:
        return _KAFKA_CLIENT_INSTANCE

    # Return dummy client if Kafka is disabled
    if not getattr(settings, "KAFKA_ENABLED", False):
        client = DummyKafkaClient()
    else:
        config = getattr(settings, "KAFKA_CONFIG", None)
        if not config:
            raise RuntimeError("KAFKA_CONFIG is not configured.")

        if not config.get("bootstrap.servers"):
            raise RuntimeError("Kafka bootstrap servers are not configured.")

        if getattr(settings, "KAFKA_DEV", False):
            client = DevKafkaClient(config)
        else:
            client = ProdKafkaClient(config)

    _KAFKA_CLIENT_INSTANCE = client
    return client
