from datetime import date, datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from thunderstore.ts_analytics.kafka import (
    DummyKafkaClient,
    KafkaClient,
    get_kafka_client,
)
from thunderstore.ts_analytics.signals import format_datetime
from thunderstore.ts_analytics.tasks import send_kafka_message

# ======================================================================
# CORE FIXTURES AND MOCKS
# ======================================================================


@pytest.fixture
def mock_producer():
    """Mocks the confluent_kafka.Producer object."""
    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        mock_producer_instance = mock_producer_cls.return_value
        yield mock_producer_instance


@pytest.fixture
def clear_kafka_client_instance():
    """Clears the module-level singleton instance before and after tests."""
    with patch("thunderstore.ts_analytics.kafka._KAFKA_CLIENT_INSTANCE", new=None):
        yield


@pytest.fixture
def mock_kafka_client():
    """Mocks the entire Kafka client retrieval process."""
    with patch("thunderstore.ts_analytics.kafka.get_kafka_client") as mock_get_client:
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance


# ======================================================================
# KAFKA MESSAGE SENDING TESTS (CELERY TASK EXECUTION)
# ======================================================================


@pytest.mark.django_db
def test_send_kafka_message_task_sends_to_client(mock_kafka_client):
    """
    Tests that the send_kafka_message_task (which is executed in the Celery worker)
    correctly retrieves the Kafka client and calls its send method.
    """
    test_topic = "test-topic"
    test_payload_string = '{"user_id": 456, "action": "updated"}'
    test_key = "user_456"

    # Call the task function directly to simulate execution in the Celery worker
    send_kafka_message(
        topic=test_topic, payload_string=test_payload_string, key=test_key
    )

    # Assert that the client was retrieved and its send method was called correctly
    mock_kafka_client.send.assert_called_once_with(
        topic=test_topic,
        payload_string=test_payload_string,
        key=test_key,
    )


def test_send_kafka_message_task_handles_none_key(mock_kafka_client):
    """Tests that the task handles a None key correctly."""
    test_topic = "test-topic-no-key"
    test_payload_string = '{"data": "no_key"}'

    # Call the task function directly to simulate execution in the Celery worker
    send_kafka_message(topic=test_topic, payload_string=test_payload_string, key=None)

    # Assert that the client was retrieved and its send method was called correctly
    mock_kafka_client.send.assert_called_once_with(
        topic=test_topic,
        payload_string=test_payload_string,
        key=None,
    )


# ======================================================================
# KAFKA CLIENT TESTS
# ======================================================================


@pytest.mark.parametrize(
    "prefix, topic, expected",
    (
        (None, "test.topic", "test.topic"),
        ("prod", "test.topic", "prod.test.topic"),
        ("dev", "test.topic", "dev.test.topic"),
        ("foobar", "prod.test", "foobar.prod.test"),
    ),
)
def test_kafka_client_prefixes_topic(
    mock_producer,
    prefix: Optional[str],
    topic: str,
    expected: str,
):
    """Test KafkaClient applies topic prefix"""
    from thunderstore.ts_analytics.kafka import KafkaClient

    client = KafkaClient(
        topic_prefix=prefix, producer_config={"bootstrap.servers": "test:9092"}
    )
    payload_string = '{"message": "dev_test"}'
    key = "dev_key"

    client.send(topic=topic, payload_string=payload_string, key=key)

    mock_producer.produce.assert_called_once_with(
        topic=expected,
        value=payload_string.encode("utf-8"),
        key=key.encode("utf-8"),
    )


def test_get_kafka_client_disabled(settings, clear_kafka_client_instance):
    """Test get_kafka_client returns DummyKafkaClient when Kafka is disabled."""
    settings.KAFKA_ENABLED = False
    client = get_kafka_client()
    assert isinstance(client, DummyKafkaClient)


def test_get_kafka_client_singleton(settings, clear_kafka_client_instance):
    """Test that the client is a singleton, regardless of client type."""
    from thunderstore.ts_analytics.kafka import KafkaClient

    settings.KAFKA_ENABLED = True
    settings.KAFKA_TOPIC_PREFIX = "prod"
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client1 = get_kafka_client()
        client2 = get_kafka_client()

    assert client1 is client2
    assert isinstance(client1, KafkaClient)
    assert mock_producer_cls.call_count == 1


def test_get_kafka_client_runtime_error_no_config(
    settings, clear_kafka_client_instance
):
    """Test for RuntimeError when KAFKA_ENABLED is True but KAFKA_CONFIG is None."""
    settings.KAFKA_ENABLED = True
    settings.KAFKA_CONFIG = None

    with pytest.raises(RuntimeError, match="KAFKA_CONFIG is not configured."):
        get_kafka_client()


def test_get_kafka_client_runtime_error_no_bootstrap_servers(
    settings, clear_kafka_client_instance
):
    """Test for RuntimeError when KAFKA_ENABLED is True but no bootstrap.servers are set."""
    settings.KAFKA_ENABLED = True
    settings.KAFKA_CONFIG = {"linger.ms": 100}

    with pytest.raises(
        RuntimeError, match="Kafka bootstrap servers are not configured."
    ):
        get_kafka_client()


def test_kafka_client_close_handles_flush(mock_producer, capfd):
    """
    Tests that KafkaClient.close() calls producer.flush with the correct timeout
    and prints a warning if messages remain in the queue.
    """
    client = KafkaClient(
        topic_prefix=None,
        producer_config={"bootstrap.servers": "test:9092"},
    )

    # --- Scenario 1: Successful flush (0 remaining messages) ---
    mock_producer.flush.return_value = 0

    client.close()
    mock_producer.flush.assert_called_once_with(timeout=10)

    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    mock_producer.flush.reset_mock()

    # --- Scenario 2: Unsuccessful flush (5 remaining messages) ---
    mock_producer.flush.return_value = 5

    client.close()

    mock_producer.flush.assert_called_once_with(timeout=10)

    captured = capfd.readouterr()
    expected_warning = "WARNING: 5 messages still in queue after flush."
    assert expected_warning in captured.out


class FormatDateTimeTest(TestCase):
    def test_string_and_none_inputs(self):
        """Tests cases where input should be returned unchanged or as None."""
        self.assertIsNone(format_datetime(None))

        test_string = "2023-10-25T10:00:00+00:00"
        self.assertEqual(format_datetime(test_string), test_string)

    def test_valid_datetime_and_date_inputs(self):
        """Tests standard datetime and date objects which support isoformat()."""
        dt_obj = datetime(2023, 10, 25, 10, 30, 0, 123456)
        expected_dt_format = "2023-10-25T10:30:00.123456"
        self.assertEqual(format_datetime(dt_obj), expected_dt_format)

        date_obj = date(2024, 1, 15)
        expected_date_format = "2024-01-15"
        self.assertEqual(format_datetime(date_obj), expected_date_format)

    def test_invalid_inputs(self):
        """Tests objects that should result in None."""
        self.assertIsNone(format_datetime(12345))
        self.assertIsNone(format_datetime({"key": "value"}))
        self.assertIsNone(format_datetime([1, 2, 3]))
