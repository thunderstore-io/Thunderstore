import json
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.db import transaction
from django.test import TestCase

from thunderstore.ts_analytics.kafka import (
    DummyKafkaClient,
    KafkaClient,
    KafkaTopic,
    get_kafka_client,
    send_kafka_message,
    send_kafka_message_task,
)

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


@pytest.fixture(autouse=True)
def mock_celery_task_delay():
    """Mocks the Celery task's .delay() method to prevent actual Celery calls."""
    with patch(
        "thunderstore.ts_analytics.kafka.send_kafka_message_task.delay"
    ) as mock_delay:
        yield mock_delay


@pytest.fixture
def fake_commit_executor():
    """
    Mocks transaction.on_commit to capture callbacks for execution after the test.
    Used for testing send_kafka_message, which is deferred on commit.
    """
    callbacks = []

    def fake_on_commit(func, *args, **kwargs):
        callbacks.append(func)

    # Patch the function where it is defined
    with patch("django.db.transaction.on_commit", side_effect=fake_on_commit):
        yield callbacks  # Yield the list of captured callbacks

    # After the test, manually run the captured callbacks to simulate transaction commit
    for callback in callbacks:
        callback()


# ======================================================================
# KAFKA CLIENT & ASYNC TASK TESTS
# ======================================================================


class KafkaMessageQueueingTest(TestCase):
    # This ensures that any 'transaction.on_commit' call in the test
    # executes its callback immediately, simulating a successful commit.
    # We patch the actual send_kafka_message_task.delay to verify the call.
    @patch("thunderstore.ts_analytics.kafka.send_kafka_message_task")
    @patch("django.db.transaction.on_commit", side_effect=lambda func: func())
    def test_send_kafka_message_queues_task_on_commit(
        self, mock_on_commit: MagicMock, mock_send_task: MagicMock
    ):
        # 1. Define test data
        test_topic = "test-topic"
        test_payload = {"user_id": 123, "action": "created"}
        test_key = "user_123"
        expected_payload_string = json.dumps(test_payload)

        # 2. Call the function to be tested
        send_kafka_message(topic=test_topic, payload=test_payload, key=test_key)

        # 3. Assertions

        # A. Check that transaction.on_commit was called
        # This confirms the message queuing is guarded by the commit logic.
        mock_on_commit.assert_called_once()

        # B. Check that the task's .delay() method was called
        # This confirms the Celery task was queued.
        mock_send_task.delay.assert_called_once()

        # C. Check that the task was called with the correct arguments
        # This ensures data integrity and correct routing.
        mock_send_task.delay.assert_called_with(
            topic=test_topic,
            payload_string=expected_payload_string,
            key=test_key,
        )

    @patch("thunderstore.ts_analytics.kafka.send_kafka_message_task")
    def test_send_kafka_message_does_not_queue_immediately_in_transaction(
        self, mock_send_task: MagicMock
    ):
        test_topic = "test-topic-2"
        test_payload = {"data": "test"}

        # Use a manual transaction block
        with transaction.atomic():
            send_kafka_message(topic=test_topic, payload=test_payload)

            # Assert that the task was *not* called yet,
            # because the transaction hasn't been committed.
            mock_send_task.delay.assert_not_called()


def test_kafka_client_send(mock_producer):
    """Test the KafkaClient's send method correctly calls producer.produce."""
    client = KafkaClient({"bootstrap.servers": "test:9092"})
    topic = "test.topic"
    payload_string = '{"message": "hello"}'
    key = "test_key"

    client.send(topic=topic, payload_string=payload_string, key=key)

    mock_producer.produce.assert_called_once_with(
        topic=topic,
        value=payload_string.encode("utf-8"),
        key=key.encode("utf-8"),
    )


def test_kafka_client_send_no_key(mock_producer):
    """Test send method with a None key."""
    client = KafkaClient({"bootstrap.servers": "test:9092"})
    topic = "test.topic"
    payload_string = '{"message": "hello"}'

    client.send(topic=topic, payload_string=payload_string, key=None)

    mock_producer.produce.assert_called_once_with(
        topic=topic,
        value=payload_string.encode("utf-8"),
        key=None,
    )


def test_kafka_client_close(mock_producer):
    """Test the KafkaClient's close method correctly calls producer.flush."""
    client = KafkaClient({"bootstrap.servers": "test:9092"})
    mock_producer.flush.return_value = 0

    client.close()

    mock_producer.flush.assert_called_once_with(timeout=10)


def test_dummy_kafka_client_send():
    """Test that DummyKafkaClient.send does nothing."""
    client = DummyKafkaClient()
    client.send(topic="dummy", payload_string="{}")


# --- get_kafka_client Tests ---


def test_get_kafka_client_disabled(settings, clear_kafka_client_instance):
    """Test get_kafka_client returns DummyKafkaClient when Kafka is disabled."""
    settings.KAFKA_ENABLED = False
    client = get_kafka_client()
    assert isinstance(client, DummyKafkaClient)


def test_get_kafka_client_enabled(settings, mock_producer, clear_kafka_client_instance):
    """Test get_kafka_client returns KafkaClient when enabled and configured."""
    settings.KAFKA_ENABLED = True
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    # FIX: Capture the mock class object explicitly
    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client = get_kafka_client()
        assert isinstance(client, KafkaClient)

    # Assert on the mock class object
    mock_producer_cls.assert_called_once_with(settings.KAFKA_CONFIG)


def test_get_kafka_client_singleton(
    settings, mock_producer, clear_kafka_client_instance
):
    """Test that the client is a singleton."""
    settings.KAFKA_ENABLED = True
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    # FIX: Capture the mock class object explicitly
    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client1 = get_kafka_client()
        client2 = get_kafka_client()

    assert client1 is client2
    # Assert on the mock class object
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


# --- send_kafka_message_task Tests ---


def test_send_kafka_message_task_sends_message(
    mock_producer, clear_kafka_client_instance, settings
):
    """Test the Celery task calls the KafkaClient's send method."""
    settings.KAFKA_ENABLED = True
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    mock_client_instance = MagicMock(spec=KafkaClient)
    with patch(
        "thunderstore.ts_analytics.kafka.get_kafka_client",
        return_value=mock_client_instance,
    ):
        topic = "test.topic"
        payload_string = '{"message": "async_test"}'
        key = "async_key"

        send_kafka_message_task(topic=topic, payload_string=payload_string, key=key)

        mock_client_instance.send.assert_called_once_with(
            topic=topic,
            payload_string=payload_string,
            key=key,
        )
