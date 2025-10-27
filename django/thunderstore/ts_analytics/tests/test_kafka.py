import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from django.db.transaction import TransactionManagementError
from django.test import TestCase

from thunderstore.ts_analytics.kafka import (
    DummyKafkaClient,
    KafkaClient,
    get_kafka_client,
    send_kafka_message,
)
from thunderstore.ts_analytics.signals import format_datetime

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
def mock_kafka_client_instance():
    """Mocks the get_kafka_client function to return a mock client."""
    mock_client = MagicMock()
    with patch(
        "thunderstore.ts_analytics.kafka.get_kafka_client", return_value=mock_client
    ):
        yield mock_client


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
# KAFKA MESSAGE SENDING TESTS (DEFERRED EXECUTION)
# ======================================================================


@pytest.mark.django_db
def test_send_kafka_message_executes_on_commit(
    mock_kafka_client_instance, fake_commit_executor
):
    """
    Tests that send_kafka_message defers execution until the transaction commits,
    then executes the Kafka client send call with the correct arguments.
    """
    test_topic = "test-topic"
    test_payload = {"user_id": 456, "action": "updated"}
    test_key = "user_456"
    expected_payload_string = json.dumps(test_payload)

    send_kafka_message(topic=test_topic, payload=test_payload, key=test_key)

    mock_kafka_client_instance.send.assert_not_called()
    assert len(fake_commit_executor) == 1

    # Manually run the captured callback to simulate the transaction commit and trigger the send
    for callback in fake_commit_executor:
        callback()

    mock_kafka_client_instance.send.assert_called_once_with(
        topic=test_topic,
        payload_string=expected_payload_string,
        key=test_key,
    )


@pytest.mark.django_db
def test_send_kafka_message_executes_immediately_without_transaction(
    mock_kafka_client_instance,
):
    """
    Tests that if no transaction is active, the message is sent immediately.
    """
    # Patch on_commit to raise TransactionManagementError to simulate the "no active transaction" state.
    with patch(
        "django.db.transaction.on_commit", side_effect=TransactionManagementError
    ):
        test_topic = "test-topic-immediate"
        test_payload = {"data": "no_txn"}
        expected_payload_string = json.dumps(test_payload)

        # The function executes immediately because the patched on_commit raises the error
        send_kafka_message(topic=test_topic, payload=test_payload)

    # Assert that the client.send was called immediately
    mock_kafka_client_instance.send.assert_called_once_with(
        topic=test_topic,
        payload_string=expected_payload_string,
        key=None,
    )


def test_base_kafka_client_send_no_prefix(mock_producer):
    """Test base KafkaClient's send method sends without a prefix (used internally by Dev/Prod)."""
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


def test_dev_kafka_client_send_prefixes_topic(mock_producer):
    """Test DevKafkaClient prefixes the topic with 'dev.'."""
    from thunderstore.ts_analytics.kafka import DevKafkaClient

    client = DevKafkaClient({"bootstrap.servers": "test:9092"})
    original_topic = "test.topic"
    expected_topic = "dev.test.topic"
    payload_string = '{"message": "dev_test"}'
    key = "dev_key"

    client.send(topic=original_topic, payload_string=payload_string, key=key)

    mock_producer.produce.assert_called_once_with(
        topic=expected_topic,
        value=payload_string.encode("utf-8"),
        key=key.encode("utf-8"),
    )


def test_prod_kafka_client_send_prefixes_topic(mock_producer):
    """Test ProdKafkaClient prefixes the topic with 'prod.'."""
    from thunderstore.ts_analytics.kafka import ProdKafkaClient

    client = ProdKafkaClient({"bootstrap.servers": "test:9092"})
    original_topic = "test.topic"
    expected_topic = "prod.test.topic"
    payload_string = '{"message": "prod_test"}'
    key = "prod_key"

    client.send(topic=original_topic, payload_string=payload_string, key=key)

    mock_producer.produce.assert_called_once_with(
        topic=expected_topic,
        value=payload_string.encode("utf-8"),
        key=key.encode("utf-8"),
    )


def test_get_kafka_client_disabled(settings, clear_kafka_client_instance):
    """Test get_kafka_client returns DummyKafkaClient when Kafka is disabled."""
    settings.KAFKA_ENABLED = False
    client = get_kafka_client()
    assert isinstance(client, DummyKafkaClient)


def test_get_kafka_client_enabled_prod(settings, clear_kafka_client_instance):
    """Test get_kafka_client returns ProdKafkaClient when enabled and KAFKA_DEV is False (default)."""
    from thunderstore.ts_analytics.kafka import ProdKafkaClient

    settings.KAFKA_ENABLED = True
    settings.KAFKA_DEV = False
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client = get_kafka_client()
        assert isinstance(client, ProdKafkaClient)

    # Assert on the mock class object
    mock_producer_cls.assert_called_once_with(settings.KAFKA_CONFIG)


def test_get_kafka_client_enabled_dev(settings, clear_kafka_client_instance):
    """Test get_kafka_client returns DevKafkaClient when enabled and KAFKA_DEV is True."""
    from thunderstore.ts_analytics.kafka import DevKafkaClient

    settings.KAFKA_ENABLED = True
    settings.KAFKA_DEV = True
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client = get_kafka_client()
        assert isinstance(client, DevKafkaClient)

    # Assert on the mock class object
    mock_producer_cls.assert_called_once_with(settings.KAFKA_CONFIG)


def test_get_kafka_client_singleton(settings, clear_kafka_client_instance):
    """Test that the client is a singleton, regardless of client type."""
    from thunderstore.ts_analytics.kafka import ProdKafkaClient

    settings.KAFKA_ENABLED = True
    settings.KAFKA_DEV = False
    settings.KAFKA_CONFIG = {"bootstrap.servers": "test:9092"}

    with patch("thunderstore.ts_analytics.kafka.Producer") as mock_producer_cls:
        client1 = get_kafka_client()
        client2 = get_kafka_client()

    assert client1 is client2
    assert isinstance(client1, ProdKafkaClient)
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


def test_kafka_client_close_handles_flush(mock_producer, capfd):
    """
    Tests that KafkaClient.close() calls producer.flush with the correct timeout
    and prints a warning if messages remain in the queue.
    """
    client = KafkaClient({"bootstrap.servers": "test:9092"})

    # --- Scenario 1: Successful flush (0 remaining messages) ---
    mock_producer.flush.return_value = 0

    client.close()

    # Assert flush was called correctly
    mock_producer.flush.assert_called_once_with(timeout=10)

    # Assert nothing was printed
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    mock_producer.flush.reset_mock()  # Reset mock call count for the next scenario

    # --- Scenario 2: Unsuccessful flush (5 remaining messages) ---
    mock_producer.flush.return_value = 5

    client.close()

    # Assert flush was called correctly again
    mock_producer.flush.assert_called_once_with(timeout=10)

    # Assert warning was printed
    captured = capfd.readouterr()
    expected_warning = "WARNING: 5 messages still in queue after flush."
    assert expected_warning in captured.out


class FormatDateTimeTest(TestCase):
    def test_string_and_none_inputs(self):
        """Tests cases where input should be returned unchanged or as None."""
        # 1. None input
        self.assertIsNone(format_datetime(None))

        # 2. String input
        test_string = "2023-10-25T10:00:00+00:00"
        self.assertEqual(format_datetime(test_string), test_string)

    def test_valid_datetime_and_date_inputs(self):
        """Tests standard datetime and date objects which support isoformat()."""

        # 1. Timezone-naive datetime object
        dt_obj = datetime(2023, 10, 25, 10, 30, 0, 123456)
        expected_dt_format = "2023-10-25T10:30:00.123456"
        self.assertEqual(format_datetime(dt_obj), expected_dt_format)

        # 2. Date object
        date_obj = date(2024, 1, 15)
        expected_date_format = "2024-01-15"
        self.assertEqual(format_datetime(date_obj), expected_date_format)

    def test_invalid_inputs(self):
        """Tests objects that should result in None."""

        # 1. Invalid object inputs (should raise AttributeError, resulting in None)
        self.assertIsNone(format_datetime(12345))
        self.assertIsNone(format_datetime({"key": "value"}))
        self.assertIsNone(format_datetime([1, 2, 3]))
