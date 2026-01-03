from datetime import date, timedelta
from typing import Dict, List, Tuple, TypedDict

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.models import Package, PackageVersion


class DailyDownloadMetrics(TypedDict):
    date: date
    count: int


class PackageVersionDownloadMetrics(TypedDict):
    namespace: str
    name: str
    version_number: str
    total_downloads: int
    daily_downloads: List[DailyDownloadMetrics]


class PackageDownloadMetrics(TypedDict):
    namespace: str
    name: str
    total_downloads: int
    daily_downloads: List[DailyDownloadMetrics]


def _calculate_date_range(days: int) -> Tuple[date, date]:
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _fill_missing_dates(
    download_events: List[Dict],
    start_date: date,
    end_date: date,
) -> List[DailyDownloadMetrics]:
    download_dict = {item["date"]: item["count"] for item in download_events}
    daily_downloads = []

    current_date = start_date
    while current_date <= end_date:
        daily_downloads.append(
            {
                "date": current_date,
                "count": download_dict.get(current_date, 0),
            }
        )
        current_date += timedelta(days=1)

    return daily_downloads


def get_package_version_download_metrics(
    version: PackageVersion,
    days: int,
) -> PackageVersionDownloadMetrics:
    """
    Get historical download metrics for a specific package version.
    """
    start_date, end_date = _calculate_date_range(days)

    download_events = (
        PackageVersionDownloadEvent.objects.filter(
            version_id=version.id,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )
        .annotate(date=TruncDate("timestamp"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    daily_downloads = _fill_missing_dates(
        list(download_events),
        start_date,
        end_date,
    )

    return {
        "namespace": version.package.namespace.name,
        "name": version.name,
        "version_number": version.version_number,
        "total_downloads": version.downloads,
        "daily_downloads": daily_downloads,
    }


def get_package_download_metrics(
    package: Package,
    days: int,
) -> PackageDownloadMetrics:
    """
    Get aggregated historical download metrics for all versions of a package.
    """
    start_date, end_date = _calculate_date_range(days)

    version_ids = list(
        package.versions.filter(is_active=True).values_list("id", flat=True)
    )

    download_events = (
        PackageVersionDownloadEvent.objects.filter(
            version_id__in=version_ids,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )
        .annotate(date=TruncDate("timestamp"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    daily_downloads = _fill_missing_dates(
        list(download_events),
        start_date,
        end_date,
    )

    return {
        "namespace": package.namespace.name,
        "name": package.name,
        "total_downloads": package.downloads,
        "daily_downloads": daily_downloads,
    }

