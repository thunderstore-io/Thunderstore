import json
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, Optional, Union

from confluent_kafka import Producer
from django.conf import settings


class KafkaTopics(str, Enum):
    METRICS_DOWNLOADS = "ts.metrics.package.downloads"


def send_kafka_message(topic: KafkaTopics, payload: dict, key: Optional[str] = None):
    client = get_kafka_client()
    client.send(topic=topic, payload=payload, key=key)


class KafkaClient:
    def __init__(self, config: Dict[str, Any]):
        self._producer = Producer(config)

    def send(
        self,
        topic: KafkaTopics,
        payload: dict,
        key: Optional[str] = None,
    ):
        try:
            value_bytes = json.dumps(payload).encode("utf-8")
            key_bytes = key.encode("utf-8") if key else None
        except TypeError as e:
            print(f"Failed to serialize payload to JSON for topic {topic}: {e}")
            return

        try:
            self._producer.produce(
                topic=topic.value,
                value=value_bytes,
                key=key_bytes,
            )

            self._producer.poll(0)
        except Exception as e:
            print("Error producing message in kafka: " + e.__str__())


@lru_cache(maxsize=1)
def get_kafka_client() -> KafkaClient:
    config = getattr(settings, "KAFKA_CONFIG", None)
    if not config:
        raise RuntimeError("KAFKA_CONFIG is not configured.")

    if not config.get("bootstrap.servers"):
        raise RuntimeError("Kafka bootstrap servers are not configured.")

    return KafkaClient(config)
