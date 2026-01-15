from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from thunderstore.community.models import PackageListing
from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.models import Package, PackageVersion


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_package_version_metrics_url(
    namespace: str,
    package_name: str,
    version_number: str,
) -> str:
    return (
        f"/api/cyberstorm/package/{namespace}/"
        f"{package_name}/v/{version_number}/metrics/downloads/"
    )


def get_package_metrics_url(namespace: str, package_name: str) -> str:
    return f"/api/cyberstorm/package/{namespace}/{package_name}/metrics/downloads/"


# ---------------------------------------------------------------------------
# Package version download metrics tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_package_version_download_metrics_endpoint(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test getting download metrics for a specific package version."""
    package = active_package_listing.package
    version = package.latest

    # Create some download events over the past few days
    now = timezone.now()
    for days_ago in range(5):
        timestamp = now - timedelta(days=days_ago)
        for _ in range(days_ago + 1):  # More downloads for older dates
            PackageVersionDownloadEvent.objects.create(
                version_id=version.id,
                timestamp=timestamp,
            )

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert "namespace" in data
    assert "name" in data
    assert "version_number" in data
    assert "total_downloads" in data
    assert "daily_downloads" in data

    assert data["namespace"] == package.namespace.name
    assert data["name"] == package.name
    assert data["version_number"] == version.version_number
    assert isinstance(data["daily_downloads"], list)
    assert len(data["daily_downloads"]) == 30  # Default is 30 days

    # Check that each day has the expected structure
    for day_data in data["daily_downloads"]:
        assert "date" in day_data
        assert "count" in day_data
        assert isinstance(day_data["count"], int)
        assert day_data["count"] >= 0


@pytest.mark.django_db
def test_package_version_download_metrics_with_custom_days(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test getting download metrics with a custom number of days."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )
    api_path = f"{api_path}?days=7"

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert len(data["daily_downloads"]) == 7


@pytest.mark.django_db
@pytest.mark.parametrize("days", [0, -1, 366, 400, 1000])
def test_package_version_download_metrics_invalid_days(
    api_client: APIClient,
    active_package_listing: PackageListing,
    days: int,
):
    """Test that invalid day values are rejected."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(f"{api_path}?days={days}")
    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("days", [1, 7, 30, 90, 180, 365])
def test_package_version_download_metrics_valid_days(
    api_client: APIClient,
    active_package_listing: PackageListing,
    days: int,
):
    """Test that valid day values are accepted."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(f"{api_path}?days={days}")
    assert response.status_code == 200

    data = response.json()
    assert len(data["daily_downloads"]) == days


@pytest.mark.django_db
def test_package_version_download_metrics_not_found(
    api_client: APIClient,
):
    """Test that a 404 is returned for a non-existent package version."""
    api_path = get_package_version_metrics_url(
        "NonExistent",
        "NonExistentPackage",
        "1.0.0",
    )

    response = api_client.get(api_path)
    assert response.status_code == 404


@pytest.mark.django_db
def test_package_version_download_metrics_no_events(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test metrics endpoint with no download events."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert len(data["daily_downloads"]) == 30
    # All days should have 0 downloads
    for day_data in data["daily_downloads"]:
        assert day_data["count"] == 0


@pytest.mark.django_db
def test_package_version_download_metrics_date_range(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that download metrics correctly covers the requested date range."""
    package = active_package_listing.package
    version = package.latest

    # Create download events for specific dates
    now = timezone.now()
    for days_ago in [0, 3, 6]:
        timestamp = now - timedelta(days=days_ago)
        PackageVersionDownloadEvent.objects.create(
            version_id=version.id,
            timestamp=timestamp,
        )

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(f"{api_path}?days=7")
    assert response.status_code == 200

    data = response.json()
    daily_downloads = data["daily_downloads"]

    days_with_downloads = sum(1 for day in daily_downloads if day["count"] > 0)
    assert days_with_downloads == 3

    dates = [day["date"] for day in daily_downloads]
    assert dates == sorted(dates)


@pytest.mark.django_db
def test_package_version_download_metrics_date_format(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that dates are returned in the correct format."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    for day_data in data["daily_downloads"]:
        date_str = day_data["date"]
        # Date should be in YYYY-MM-DD format
        parts = date_str.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 2  # day


@pytest.mark.django_db
def test_package_version_download_metrics_total_downloads(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that total_downloads reflects the version's all-time downloads."""
    package = active_package_listing.package
    version = package.latest

    # Set a specific download count
    version.downloads = 12345
    version.save(update_fields=["downloads"])

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert data["total_downloads"] == 12345


# ---------------------------------------------------------------------------
# Package download metrics tests (aggregated across versions)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_package_download_metrics_endpoint(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test getting aggregated download metrics for all versions of a package."""
    package = active_package_listing.package

    # Create some download events for different versions
    now = timezone.now()
    for version in package.versions.filter(is_active=True):
        for days_ago in range(3):
            timestamp = now - timedelta(days=days_ago)
            for _ in range(2):
                PackageVersionDownloadEvent.objects.create(
                    version_id=version.id,
                    timestamp=timestamp,
                )

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert "namespace" in data
    assert "name" in data
    assert "total_downloads" in data
    assert "daily_downloads" in data

    assert data["namespace"] == package.namespace.name
    assert data["name"] == package.name
    assert isinstance(data["daily_downloads"], list)
    assert len(data["daily_downloads"]) == 30  # Default is 30 days


@pytest.mark.django_db
def test_package_download_metrics_with_custom_days(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test getting aggregated download metrics with a custom number of days."""
    package = active_package_listing.package

    api_path = f"{get_package_metrics_url(package.namespace.name, package.name)}?days=14"

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert len(data["daily_downloads"]) == 14


@pytest.mark.django_db
@pytest.mark.parametrize("days", [0, -1, 366, 400, 1000])
def test_package_download_metrics_invalid_days(
    api_client: APIClient,
    active_package_listing: PackageListing,
    days: int,
):
    """Test that invalid day values are rejected for package metrics."""
    package = active_package_listing.package

    api_path = f"{get_package_metrics_url(package.namespace.name, package.name)}?days={days}"

    response = api_client.get(api_path)
    assert response.status_code == 400


@pytest.mark.django_db
def test_package_download_metrics_not_found(
    api_client: APIClient,
):
    """Test that a 404 is returned for a non-existent package."""
    api_path = get_package_metrics_url("NonExistent", "NonExistentPackage")

    response = api_client.get(api_path)
    assert response.status_code == 404


@pytest.mark.django_db
def test_package_download_metrics_no_events(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test metrics endpoint with no download events."""
    package = active_package_listing.package

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert len(data["daily_downloads"]) == 30
    # All days should have 0 downloads
    for day_data in data["daily_downloads"]:
        assert day_data["count"] == 0


@pytest.mark.django_db
def test_package_download_metrics_total_downloads(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that total_downloads reflects the package's all-time downloads."""
    package = active_package_listing.package

    # Set a specific download count on the version
    # Package.downloads is a cached_property that aggregates from versions
    version = package.latest
    version.downloads = 54321
    version.save(update_fields=["downloads"])

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    assert data["total_downloads"] == 54321


@pytest.mark.django_db
def test_package_download_metrics_multiple_versions(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that package metrics aggregate downloads across multiple versions."""
    from thunderstore.repository.factories import PackageVersionFactory

    package = active_package_listing.package

    # Create additional versions
    version2 = PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="1.0.1",
        is_active=True,
    )
    version3 = PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="1.0.2",
        is_active=True,
    )

    # Create download events for different versions on the same day
    now = timezone.now()
    timestamp = now - timedelta(days=1)

    # 3 downloads for latest version
    for _ in range(3):
        PackageVersionDownloadEvent.objects.create(
            version_id=package.latest.id,
            timestamp=timestamp,
        )

    # 5 downloads for version2
    for _ in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=version2.id,
            timestamp=timestamp,
        )

    # 2 downloads for version3
    for _ in range(2):
        PackageVersionDownloadEvent.objects.create(
            version_id=version3.id,
            timestamp=timestamp,
        )

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    daily_downloads = data["daily_downloads"]

    # Find the day with downloads (yesterday)
    days_with_downloads = [d for d in daily_downloads if d["count"] > 0]
    assert len(days_with_downloads) >= 1

    # The day should have the sum of all version downloads (3 + 5 + 2 = 10)
    total_downloads_yesterday = sum(d["count"] for d in days_with_downloads)
    assert total_downloads_yesterday == 10


@pytest.mark.django_db
def test_package_download_metrics_only_active_versions(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that only active versions are included in aggregated metrics."""
    from thunderstore.repository.factories import PackageVersionFactory

    package = active_package_listing.package

    # Create an inactive version
    inactive_version = PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="0.9.0",
        is_active=False,
    )

    # Create download events for both versions
    now = timezone.now()
    timestamp = now - timedelta(days=1)

    # 5 downloads for active version
    for _ in range(5):
        PackageVersionDownloadEvent.objects.create(
            version_id=package.latest.id,
            timestamp=timestamp,
        )

    # 10 downloads for inactive version (should be ignored)
    for _ in range(10):
        PackageVersionDownloadEvent.objects.create(
            version_id=inactive_version.id,
            timestamp=timestamp,
        )

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    daily_downloads = data["daily_downloads"]

    # Find the day with downloads
    days_with_downloads = [d for d in daily_downloads if d["count"] > 0]

    # Should only count the 5 downloads from active version
    total_downloads_yesterday = sum(d["count"] for d in days_with_downloads)
    assert total_downloads_yesterday == 5


@pytest.mark.django_db
def test_package_version_download_metrics_inactive_version(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that 404 is returned for inactive version."""
    from thunderstore.repository.factories import PackageVersionFactory

    package = active_package_listing.package

    # Create an inactive version
    inactive_version = PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="0.9.0",
        is_active=False,
    )

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        inactive_version.version_number,
    )

    response = api_client.get(api_path)
    assert response.status_code == 404


@pytest.mark.django_db
def test_package_download_metrics_inactive_package(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that 404 is returned for inactive package."""
    package = active_package_listing.package

    # Make package inactive
    package.is_active = False
    package.save(update_fields=["is_active"])

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 404


@pytest.mark.django_db
def test_package_download_metrics_date_ordering(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that daily downloads are returned in ascending date order."""
    package = active_package_listing.package

    api_path = get_package_metrics_url(
        package.namespace.name,
        package.name,
    )

    response = api_client.get(api_path)
    assert response.status_code == 200

    data = response.json()
    dates = [day["date"] for day in data["daily_downloads"]]

    # Verify dates are in ascending order
    assert dates == sorted(dates)


@pytest.mark.django_db
def test_package_version_download_metrics_invalid_query_param(
    api_client: APIClient,
    active_package_listing: PackageListing,
):
    """Test that non-numeric days parameter is rejected."""
    package = active_package_listing.package
    version = package.latest

    api_path = get_package_version_metrics_url(
        package.namespace.name,
        package.name,
        version.version_number,
    )

    response = api_client.get(f"{api_path}?days=invalid")
    assert response.status_code == 400
