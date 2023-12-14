from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from thunderstore.metrics.models import (
    PackageVersionDownloadEvent as TimeseriesDownloadEvent,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.models import (
    PackageVersionDownloadEvent as LegacyDownloadEvent,
)


@pytest.mark.django_db
def test_download_metrics__can_log_download_event__no_ip(
    package_version: PackageVersion,
):
    assert PackageVersion._can_log_download_event(package_version, None) is False


@pytest.mark.django_db
@pytest.mark.parametrize("use_legacy", (False, True))
@pytest.mark.parametrize("use_timeseries", (False, True))
def test_download_metrics__can_log_download_event__settings(
    package_version: PackageVersion,
    use_legacy: bool,
    use_timeseries: bool,
    settings: Any,
):
    settings.USE_LEGACY_PACKAGE_DOWNLOAD_METRICS = use_legacy
    settings.USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS = use_timeseries

    expected = use_legacy or use_timeseries

    assert (
        PackageVersion._can_log_download_event(
            package_version,
            "127.0.0.1",
        )
        is expected
    )


@pytest.mark.django_db
def test_download_metrics__can_log_download_event__rate_limit(
    package_version: PackageVersion,
):
    v = package_version
    ip_a = "127.0.0.1"
    ip_b = "192.168.0.1"
    assert PackageVersion._can_log_download_event(v, ip_a) is True
    assert PackageVersion._can_log_download_event(v, ip_a) is False

    assert PackageVersion._can_log_download_event(v, ip_b) is True
    assert PackageVersion._can_log_download_event(v, ip_b) is False
    assert PackageVersion._can_log_download_event(v, ip_a) is False

    cache.delete(PackageVersion._get_log_key(v, ip_b))
    assert PackageVersion._can_log_download_event(v, ip_b) is True
    assert PackageVersion._can_log_download_event(v, ip_a) is False

    cache.delete(PackageVersion._get_log_key(v, ip_a))
    assert PackageVersion._can_log_download_event(v, ip_b) is False
    assert PackageVersion._can_log_download_event(v, ip_a) is True


@pytest.mark.django_db
def test_download_metrics__log_download_event_legacy(
    package_version: PackageVersion,
):
    v = package_version
    ip = "127.0.0.1"
    assert LegacyDownloadEvent.objects.count() == 0
    PackageVersion._log_download_event_legacy(v, ip)
    assert LegacyDownloadEvent.objects.count() == 1
    event = LegacyDownloadEvent.objects.first()

    assert event.source_ip == ip
    assert event.total_downloads == 1
    assert event.counted_downloads == 1

    PackageVersion._log_download_event_legacy(v, ip)
    event.refresh_from_db()
    assert event.total_downloads == 2
    assert event.counted_downloads == 1

    event.last_download = timezone.now() - timedelta(
        seconds=settings.DOWNLOAD_METRICS_TTL_SECONDS + 1
    )
    event.save()

    PackageVersion._log_download_event_legacy(v, ip)
    event.refresh_from_db()
    assert event.total_downloads == 3
    assert event.counted_downloads == 2


@pytest.mark.django_db
def test_download_metrics__log_download_event_timeseries(
    package_version: PackageVersion,
):
    assert TimeseriesDownloadEvent.objects.count() == 0
    PackageVersion._log_download_event_timeseries(package_version)
    assert TimeseriesDownloadEvent.objects.count() == 1
    PackageVersion._log_download_event_timeseries(package_version)
    assert TimeseriesDownloadEvent.objects.count() == 2
    assert (
        TimeseriesDownloadEvent.objects.filter(version_id=package_version.id).count()
        == 2
    )


@pytest.mark.django_db
@pytest.mark.parametrize("use_legacy", (False, True))
@pytest.mark.parametrize("use_timeseries", (False, True))
def test_download_metrics__log_download_event(
    package_version: PackageVersion,
    use_legacy: bool,
    use_timeseries: bool,
    settings: Any,
    mocker,
):
    settings.USE_LEGACY_PACKAGE_DOWNLOAD_METRICS = use_legacy
    settings.USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS = use_timeseries

    precheck = mocker.spy(PackageVersion, "_can_log_download_event")
    legacy = mocker.spy(PackageVersion, "_log_download_event_legacy")
    timeseries = mocker.spy(PackageVersion, "_log_download_event_timeseries")

    should_log = use_legacy or use_timeseries
    expected_count = int(should_log)

    PackageVersion.log_download_event(package_version, "127.0.0.1")

    assert precheck.call_count == 1
    assert precheck.spy_return is should_log

    assert legacy.call_count == int(use_legacy)
    assert timeseries.call_count == int(use_timeseries)

    assert package_version.downloads == expected_count

    PackageVersion.log_download_event(package_version, "127.0.0.1")

    assert precheck.call_count == 2
    assert precheck.spy_return is False
    assert package_version.downloads == expected_count
