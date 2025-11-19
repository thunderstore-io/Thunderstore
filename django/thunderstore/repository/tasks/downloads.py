from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.db.models import F
from pydantic import BaseModel

from thunderstore.core.settings import CeleryQueues
from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.models import PackageVersion
from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message

TASK_LOG_VERSION_DOWNLOAD = "thunderstore.repository.tasks.log_version_download"


class AnalyticsEventPackageDownload(BaseModel):
    id: int
    version_id: int
    timestamp: datetime


@shared_task(
    queue=CeleryQueues.LogDownloads,
    name=TASK_LOG_VERSION_DOWNLOAD,
    ignore_result=True,
)
def log_version_download(version_id: int, timestamp: str):
    timestamp_dt = datetime.fromisoformat(timestamp)
    with transaction.atomic():
        event = PackageVersionDownloadEvent.objects.create(
            version_id=version_id,
            timestamp=timestamp_dt,
        )
        PackageVersion.objects.filter(id=version_id).update(
            downloads=F("downloads") + 1
        )

        # Celery task, but intentionally called synchronously as we're already
        # in a celery task context.
        transaction.on_commit(  # pragma: no cover
            lambda: send_kafka_message(
                topic=KafkaTopic.PACKAGE_DOWNLOADED,
                payload_string=AnalyticsEventPackageDownload(
                    id=event.id,
                    version_id=version_id,
                    timestamp=timestamp_dt,
                ).json(),
            )
        )
