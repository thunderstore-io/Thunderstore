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
