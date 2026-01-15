from datetime import timedelta

import pytest
from django.utils import timezone

from thunderstore.api.cyberstorm.services.metrics import (
    get_package_download_metrics,
    get_package_version_download_metrics,
)
from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion


@pytest.mark.django_db
def test_get_package_version_download_metrics_basic(
    active_package_listing,
):
    """Test basic package version download metrics retrieval."""
    package = active_package_listing.package
    version = package.latest

    # Create download events for the past 3 days
    now = timezone.now()
    for days_ago in range(3):
        timestamp = now - timedelta(days=days_ago)
        for _ in range(days_ago + 1):
            PackageVersionDownloadEvent.objects.create(
                version_id=version.id,
                timestamp=timestamp,
            )

    result = get_package_version_download_metrics(version, days=30)

    assert result["namespace"] == package.namespace.name
    assert result["name"] == version.name
    assert result["version_number"] == version.version_number
    assert result["total_downloads"] == version.downloads
    assert len(result["daily_downloads"]) == 30


@pytest.mark.django_db
def test_get_package_version_download_metrics_custom_days(
    active_package_listing,
):
    """Test package version metrics with custom number of days."""
    package = active_package_listing.package
    version = package.latest

    result = get_package_version_download_metrics(version, days=7)

    assert len(result["daily_downloads"]) == 7
    assert result["namespace"] == package.namespace.name


@pytest.mark.django_db
def test_get_package_version_download_metrics_zero_filled(
    active_package_listing,
):
    """Test that missing dates are zero-filled."""
    package = active_package_listing.package
    version = package.latest

    # Create downloads only for today
    now = timezone.now()
    for _ in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=now,
        )

    result = get_package_version_download_metrics(version, days=7)

    assert len(result["daily_downloads"]) == 7
    # Check that today has downloads
    today_data = result["daily_downloads"][-1]
    assert today_data["count"] == 5
    # Check that previous days have zero downloads
    for day_data in result["daily_downloads"][:-1]:
        assert day_data["count"] == 0


@pytest.mark.django_db
def test_get_package_version_download_metrics_date_ordering(
    active_package_listing,
):
    """Test that dates are in correct chronological order."""
    package = active_package_listing.package
    version = package.latest

    result = get_package_version_download_metrics(version, days=5)

    # Verify dates are consecutive and in ascending order
    daily_downloads = result["daily_downloads"]
    for i in range(len(daily_downloads) - 1):
        current_date = daily_downloads[i]["date"]
        next_date = daily_downloads[i + 1]["date"]
        assert (next_date - current_date).days == 1


@pytest.mark.django_db
def test_get_package_version_download_metrics_aggregates_same_day(
    active_package_listing,
):
    """Test that multiple downloads on the same day are aggregated."""
    package = active_package_listing.package
    version = package.latest

    # Create multiple downloads on the same day but different times
    now = timezone.now()
    base_timestamp = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for hour in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=base_timestamp + timedelta(hours=hour),
        )

    result = get_package_version_download_metrics(version, days=1)

    assert len(result["daily_downloads"]) == 1
    assert result["daily_downloads"][0]["count"] == 5


@pytest.mark.django_db
def test_get_package_download_metrics_basic(
    active_package_listing,
):
    """Test basic package download metrics aggregated across versions."""
    package = active_package_listing.package
    version = package.latest

    # Create download events
    now = timezone.now()
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=now,
        )

    result = get_package_download_metrics(package, days=30)

    assert result["namespace"] == package.namespace.name
    assert result["name"] == package.name
    assert result["total_downloads"] == package.downloads
    assert len(result["daily_downloads"]) == 30


@pytest.mark.django_db
def test_get_package_download_metrics_multiple_versions(
    active_package_listing,
):
    """Test that package metrics aggregate downloads from all versions."""
    package = active_package_listing.package
    version1 = package.latest

    # Create a second version for the same package
    version2 = PackageVersionFactory(package=package, version_number="1.0.1")

    # Create downloads for both versions on the same day
    now = timezone.now()
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=version1.id,
            timestamp=now,
        )
    for _ in range(2):
        PackageVersionDownloadEvent.objects.create(
            version_id=version2.id,
            timestamp=now,
        )

    result = get_package_download_metrics(package, days=7)

    # Should aggregate downloads from both versions
    today_data = result["daily_downloads"][-1]
    assert today_data["count"] == 5


@pytest.mark.django_db
def test_get_package_download_metrics_custom_days(
    active_package_listing,
):
    """Test package metrics with custom number of days."""
    package = active_package_listing.package

    result = get_package_download_metrics(package, days=14)

    assert len(result["daily_downloads"]) == 14


@pytest.mark.django_db
def test_get_package_download_metrics_zero_filled(
    active_package_listing,
):
    """Test that missing dates are zero-filled for package metrics."""
    package = active_package_listing.package

    # Don't create any download events
    result = get_package_download_metrics(package, days=5)

    assert len(result["daily_downloads"]) == 5
    # All days should have zero downloads
    for day_data in result["daily_downloads"]:
        assert day_data["count"] == 0


@pytest.mark.django_db
def test_get_package_download_metrics_ignores_inactive_versions(
    active_package_listing,
):
    """Test that inactive versions are not included in package metrics."""
    package = active_package_listing.package
    active_version = package.latest

    # Create an inactive version
    inactive_version = PackageVersionFactory(
        package=package,
        version_number="0.9.0",
        is_active=False,
    )

    # Create downloads for both versions
    now = timezone.now()
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=active_version.id,
            timestamp=now,
        )
    for _ in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=inactive_version.id,
            timestamp=now,
        )

    result = get_package_download_metrics(package, days=1)

    # Should only include downloads from active version
    today_data = result["daily_downloads"][-1]
    assert today_data["count"] == 3


@pytest.mark.django_db
def test_get_package_version_download_metrics_respects_date_range(
    active_package_listing,
):
    """Test that only downloads within the date range are included."""
    package = active_package_listing.package
    version = package.latest

    now = timezone.now()

    # Create downloads 10 days ago (outside 7-day range)
    old_timestamp = now - timedelta(days=10)
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=old_timestamp,
        )

    # Create downloads 2 days ago (inside 7-day range)
    recent_timestamp = now - timedelta(days=2)
    for _ in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=recent_timestamp,
        )

    result = get_package_version_download_metrics(version, days=7)

    # Only the recent downloads should be counted
    total_counted = sum(day["count"] for day in result["daily_downloads"])
    assert total_counted == 5


@pytest.mark.django_db
def test_get_package_download_metrics_respects_date_range(
    active_package_listing,
):
    """Test that only downloads within the date range are included for packages."""
    package = active_package_listing.package
    version = package.latest

    now = timezone.now()

    # Create downloads 20 days ago (outside 14-day range)
    old_timestamp = now - timedelta(days=20)
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=old_timestamp,
        )

    # Create downloads 5 days ago (inside 14-day range)
    recent_timestamp = now - timedelta(days=5)
    for _ in range(7):
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=recent_timestamp,
        )

    result = get_package_download_metrics(package, days=14)

    # Only the recent downloads should be counted
    total_counted = sum(day["count"] for day in result["daily_downloads"])
    assert total_counted == 7

