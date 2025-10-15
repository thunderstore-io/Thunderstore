import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from thunderstore.core.kafka import (
    DummyKafkaClient,
    KafkaClient,
    KafkaTopic,
    get_kafka_client,
    send_kafka_message,
    send_kafka_message_async,
)


class TestKafkaTopic:
    def test_kafka_topic_enum(self):
        """Test that KafkaTopic enum has the expected values."""
        assert KafkaTopic.METRICS_DOWNLOADS == "ts.metrics.package.downloads"
        assert KafkaTopic.METRICS_DOWNLOADS.value == "ts.metrics.package.downloads"


class TestKafkaClient:
    @pytest.fixture
    def mock_producer(self):
        with patch("thunderstore.core.kafka.Producer") as mock_producer:
            producer_instance = MagicMock()
            mock_producer.return_value = producer_instance
            yield producer_instance

    def test_init(self, mock_producer):
        """Test that KafkaClient initializes with the provided config."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)
        assert client._producer == mock_producer

    def test_send_with_key(self, mock_producer):
        """Test sending a message with a key."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)

        topic = KafkaTopic.METRICS_DOWNLOADS
        payload = {"test": "data"}
        key = "test-key"

        client.send(topic=topic, payload=payload, key=key)

        mock_producer.produce.assert_called_once_with(
            topic=topic.value,
            value=json.dumps(payload).encode("utf-8"),
            key=key.encode("utf-8"),
        )
        mock_producer.poll.assert_called_once_with(0)

    def test_send_without_key(self, mock_producer):
        """Test sending a message without a key."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)

        topic = KafkaTopic.METRICS_DOWNLOADS
        payload = {"test": "data"}

        client.send(topic=topic, payload=payload)

        mock_producer.produce.assert_called_once_with(
            topic=topic.value,
            value=json.dumps(payload).encode("utf-8"),
            key=None,
        )
        mock_producer.poll.assert_called_once_with(0)

    def test_send_with_string_topic(self, mock_producer):
        """Test sending a message with a string topic."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)

        topic = "custom.topic"
        payload = {"test": "data"}

        client.send(topic=topic, payload=payload)

        mock_producer.produce.assert_called_once_with(
            topic=topic,
            value=json.dumps(payload).encode("utf-8"),
            key=None,
        )
        mock_producer.poll.assert_called_once_with(0)

    def test_send_with_invalid_payload(self, mock_producer):
        """Test sending a message with an invalid payload that can't be JSON serialized."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)

        topic = KafkaTopic.METRICS_DOWNLOADS
        # Create a circular reference that can't be JSON serialized
        payload = {}
        payload["self"] = payload

        client.send(topic=topic, payload=payload)

        # Verify produce was not called due to serialization error
        mock_producer.produce.assert_not_called()
        mock_producer.poll.assert_not_called()

    def test_send_with_producer_exception(self, mock_producer):
        """Test handling of exceptions from the producer."""
        config = {"bootstrap.servers": "localhost:9092"}
        client = KafkaClient(config)

        topic = KafkaTopic.METRICS_DOWNLOADS
        payload = {"test": "data"}

        # Make the producer raise an exception
        mock_producer.produce.side_effect = Exception("Test exception")

        # This should not raise an exception
        client.send(topic=topic, payload=payload)

        mock_producer.produce.assert_called_once()
        mock_producer.poll.assert_not_called()


class TestDummyKafkaClient:
    def test_send(self):
        """Test that DummyKafkaClient.send does nothing."""
        client = DummyKafkaClient()
        # This should not raise any exceptions
        client.send(
            topic=KafkaTopic.METRICS_DOWNLOADS, payload={"test": "data"}, key="test-key"
        )


class TestGetKafkaClient:
    def setup_method(self, method):
        """
        CRITICAL FIX: Clear the lru_cache for get_kafka_client before each test.
        This ensures that settings overrides (like KAFKA_ENABLED=True)
        are respected and the client initialization logic is re-run.
        """
        get_kafka_client.cache_clear()

    @override_settings(KAFKA_ENABLED=False)
    def test_get_kafka_client_disabled(self):
        """Test that get_kafka_client returns DummyKafkaClient when Kafka is disabled."""
        client = get_kafka_client()
        assert isinstance(client, DummyKafkaClient)

    @override_settings(KAFKA_ENABLED=True, KAFKA_CONFIG=None)
    def test_get_kafka_client_no_config(self):
        """Test that get_kafka_client raises RuntimeError when KAFKA_CONFIG is not set."""
        with pytest.raises(RuntimeError, match="KAFKA_CONFIG is not configured."):
            get_kafka_client()

    @override_settings(KAFKA_ENABLED=True, KAFKA_CONFIG={"client.id": "test"})
    def test_get_kafka_client_no_bootstrap_servers(self):
        """Test that get_kafka_client raises RuntimeError when bootstrap.servers is not set."""
        with pytest.raises(
            RuntimeError, match="Kafka bootstrap servers are not configured."
        ):
            get_kafka_client()

    @override_settings(
        KAFKA_ENABLED=True, KAFKA_CONFIG={"bootstrap.servers": "localhost:9092"}
    )
    def test_get_kafka_client_enabled(self):
        """Test that get_kafka_client returns KafkaClient when Kafka is enabled."""
        with patch("thunderstore.core.kafka.KafkaClient") as mock_kafka_client:
            mock_instance = MagicMock()
            mock_kafka_client.return_value = mock_instance

            client = get_kafka_client()

            assert client == mock_instance
            mock_kafka_client.assert_called_once_with(
                {"bootstrap.servers": "localhost:9092"}
            )


class TestSendKafkaMessage:
    def test_send_kafka_message(self):
        """Test that send_kafka_message calls client.send with the correct arguments."""
        mock_client = MagicMock()

        with patch(
            "thunderstore.core.kafka.get_kafka_client", return_value=mock_client
        ):
            topic = KafkaTopic.METRICS_DOWNLOADS
            payload = {"test": "data"}
            key = "test-key"

            send_kafka_message(topic=topic, payload=payload, key=key)

            mock_client.send.assert_called_once_with(
                topic=topic, payload=payload, key=key
            )


@pytest.mark.django_db
class TestSendKafkaMessageAsync:
    @patch("thunderstore.core.kafka.send_kafka_message")
    def test_send_kafka_message_async(self, mock_send_kafka_message):
        """Test that send_kafka_message_async calls send_kafka_message with the correct arguments."""
        topic = KafkaTopic.METRICS_DOWNLOADS
        payload = {"test": "data"}
        key = "test-key"

        send_kafka_message_async(topic=topic, payload=payload, key=key)

        mock_send_kafka_message.assert_called_once_with(
            topic=topic, payload=payload, key=key
        )

    @patch("thunderstore.core.kafka.send_kafka_message")
    def test_send_kafka_message_async_exception_handling(self, mock_send_kafka_message):
        """Test that send_kafka_message_async handles exceptions from send_kafka_message."""
        mock_send_kafka_message.side_effect = Exception("Test exception")

        topic = KafkaTopic.METRICS_DOWNLOADS
        payload = {"test": "data"}

        # This should not raise an exception
        send_kafka_message_async(topic=topic, payload=payload)

        mock_send_kafka_message.assert_called_once_with(
            topic=topic, payload=payload, key=None
        )
