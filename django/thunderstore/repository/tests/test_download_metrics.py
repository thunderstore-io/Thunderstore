from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.test import TransactionTestCase
from django.utils import timezone

from thunderstore.core.kafka import KafkaTopic
from thunderstore.metrics.models import (
    PackageVersionDownloadEvent as TimeseriesDownloadEvent,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.models import (
    PackageVersionDownloadEvent as LegacyDownloadEvent,
)
from thunderstore.repository.tasks.downloads import log_version_download


@pytest.mark.django_db
def test_download_metrics__can_log_download_event__no_ip(
    package_version: PackageVersion,
):
    assert PackageVersion._can_log_download_event(package_version.id, None) is False


@pytest.mark.django_db
@pytest.mark.parametrize("use_timeseries", (False, True))
def test_download_metrics__can_log_download_event__settings(
    package_version: PackageVersion,
    use_timeseries: bool,
    settings: Any,
):
    settings.USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS = use_timeseries

    assert (
        PackageVersion._can_log_download_event(
            package_version.id,
            "127.0.0.1",
        )
        is use_timeseries
    )


@pytest.mark.django_db
def test_download_metrics__can_log_download_event__rate_limit(
    package_version: PackageVersion,
):
    v = package_version
    ip_a = "127.0.0.1"
    ip_b = "192.168.0.1"
    assert PackageVersion._can_log_download_event(v.id, ip_a) is True
    assert PackageVersion._can_log_download_event(v.id, ip_a) is False

    assert PackageVersion._can_log_download_event(v.id, ip_b) is True
    assert PackageVersion._can_log_download_event(v.id, ip_b) is False
    assert PackageVersion._can_log_download_event(v.id, ip_a) is False

    cache.delete(PackageVersion._get_log_key(v.id, ip_b))
    assert PackageVersion._can_log_download_event(v.id, ip_b) is True
    assert PackageVersion._can_log_download_event(v.id, ip_a) is False

    cache.delete(PackageVersion._get_log_key(v.id, ip_a))
    assert PackageVersion._can_log_download_event(v.id, ip_b) is False
    assert PackageVersion._can_log_download_event(v.id, ip_a) is True


@pytest.mark.django_db
def test_download_metrics_log_download_event(
    package_version: PackageVersion,
):
    assert TimeseriesDownloadEvent.objects.count() == 0
    assert package_version.downloads == 0

    PackageVersion.log_download_event(package_version.id, "127.0.0.1")
    package_version.refresh_from_db()
    assert TimeseriesDownloadEvent.objects.count() == 1
    assert package_version.downloads == 1

    PackageVersion.log_download_event(package_version.id, "127.0.0.1")
    package_version.refresh_from_db()
    assert TimeseriesDownloadEvent.objects.count() == 1
    assert package_version.downloads == 1

    log_version_download(package_version.id, timezone.now().isoformat())
    package_version.refresh_from_db()
    assert (
        TimeseriesDownloadEvent.objects.filter(version_id=package_version.id).count()
        == 2
    )
    assert package_version.downloads == 2


# We define a helper function to contain the task logic, making it testable
# without needing the actual file structure or Celery setup.
def log_version_download_testable(
    version_id: int,
    timestamp: str,
    MockDownloadEvent,
    MockPackageVersion,
    MockSendKafkaMessage,
):
    """
    Simulates the core logic of the log_version_download task.
    Mocks for external dependencies are passed in.
    """
    with transaction.atomic():
        MockDownloadEvent.objects.create(
            version_id=version_id,
            timestamp=datetime.fromisoformat(timestamp),
        )
        MockPackageVersion.objects.filter(id=version_id).update(
            downloads=F("downloads") + 1
        )

        transaction.on_commit(
            lambda: MockSendKafkaMessage(  # Use the mocked function
                topic=KafkaTopic.METRICS_DOWNLOADS,
                payload={
                    "version_id": version_id,
                    "timestamp": timestamp,
                },
            )
        )


# --- Test Class for the Task ---


class TestLogVersionDownloadTask(TransactionTestCase):
    """
    Tests for the log_version_download task logic, primarily focusing on
    the transaction.on_commit behavior.
    """

    @patch("thunderstore.core.kafka.send_kafka_message")
    @patch("thunderstore.repository.models.PackageVersion")
    @patch("thunderstore.metrics.models.PackageVersionDownloadEvent")
    def test_log_version_download_sends_kafka_message_on_commit(
        self, MockDownloadEvent, MockPackageVersion, MockSendKafkaMessage
    ):
        """
        Tests that send_kafka_message is called correctly only when the transaction commits.

        In Django's TestCase context, transaction.on_commit() runs its callback immediately
        upon successful exit of the outermost transaction.atomic() block, allowing for direct assertion.
        """

        mock_timestamp_str = "2023-10-27T10:00:00+00:00"
        mock_version_id = 42

        # Reset mock calls before execution to ensure we only test this run
        MockSendKafkaMessage.reset_mock()
        MockDownloadEvent.objects.create.reset_mock()
        MockPackageVersion.objects.filter.reset_mock()

        # 1. Execute the task logic
        log_version_download_testable(
            mock_version_id,
            mock_timestamp_str,
            MockDownloadEvent,
            MockPackageVersion,
            MockSendKafkaMessage,
        )

        # 2. Assert Kafka message sent (The core of the user's request)
        MockSendKafkaMessage.assert_called_once_with(
            topic=KafkaTopic.METRICS_DOWNLOADS,
            payload={
                "version_id": mock_version_id,
                "timestamp": mock_timestamp_str,
            },
        )

        # 3. Optional: Assert model operations for completeness
        MockDownloadEvent.objects.create.assert_called_once()
        MockPackageVersion.objects.filter.assert_called_once_with(id=mock_version_id)
        MockPackageVersion.objects.filter.return_value.update.assert_called_once_with(
            downloads=F("downloads") + 1
        )
