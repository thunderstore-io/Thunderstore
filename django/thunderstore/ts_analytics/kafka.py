from enum import Enum
from typing import Any, Dict, Optional, Union

from confluent_kafka import Producer
from django.conf import settings
from pydantic import BaseModel

from thunderstore.core.utils import capture_exception


class KafkaTopic(str, Enum):
    PACKAGE_DOWNLOADED = "ts.package.downloaded"
    PACKAGE_UPDATED = "ts.package.updated"
    PACKAGE_VERSION_UPDATED = "ts.package.version.updated"
    PACKAGE_LISTING_UPDATED = "ts.package.listing.updated"
    COMMUNITY_UPDATED = "ts.community.updated"


def build_full_topic_name(*, topic_prefix: Optional[str], topic_name: str) -> str:
    return ".".join((x for x in (topic_prefix, topic_name) if x))


class KafkaClient:
    topic_prefix: Optional[str]
    _producer: Producer

    def __init__(self, *, topic_prefix: Optional[str], producer_config: Dict[str, Any]):
        self.topic_prefix = topic_prefix
        self._producer = Producer(producer_config)

    def send(
        self,
        topic: str,
        payload: BaseModel,
        key: Optional[str] = None,
    ):
        self._send_string(
            topic=topic,
            payload_string=payload.json(),
            key=key,
        )

    def _send_string(
        self,
        topic: str,
        payload_string: str,
        key: Optional[str] = None,
    ):
        full_topic_name = build_full_topic_name(
            topic_prefix=self.topic_prefix,
            topic_name=topic,
        )
        try:
            value_bytes = payload_string.encode("utf-8")
            key_bytes = key.encode("utf-8") if key else None

            self._producer.produce(
                topic=full_topic_name,
                value=value_bytes,
                key=key_bytes,
            )
        except Exception as e:
            capture_exception(e)


class DummyKafkaClient:
    """A dummy Kafka client that does nothing when Kafka is disabled."""

    def send(self, topic: str, payload: BaseModel, key: Optional[str] = None):
        pass

    def _send_string(self, topic: str, payload_string: str, key: Optional[str] = None):
        pass


_KAFKA_CLIENT_INSTANCE = None


def instantiate_kafka_client() -> Union[KafkaClient, DummyKafkaClient]:
    if settings.KAFKA_ENABLED is False:
        return DummyKafkaClient()
    else:
        return KafkaClient(
            topic_prefix=settings.KAFKA_TOPIC_PREFIX,
            producer_config=settings.KAFKA_CONFIG,
        )


def get_kafka_client() -> Union[KafkaClient, DummyKafkaClient]:
    global _KAFKA_CLIENT_INSTANCE

    if _KAFKA_CLIENT_INSTANCE is None:
        _KAFKA_CLIENT_INSTANCE = instantiate_kafka_client()

    return _KAFKA_CLIENT_INSTANCE
