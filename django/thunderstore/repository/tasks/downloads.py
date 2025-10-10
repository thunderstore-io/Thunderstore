from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.db.models import F

from thunderstore.core.kafka import KafkaTopics, PackageEvents
from thunderstore.core.settings import CeleryQueues
from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.models import PackageVersion

from ts_kafka import publish_event

TASK_LOG_VERSION_DOWNLOAD = "thunderstore.repository.tasks.log_version_download"


@shared_task(queue=CeleryQueues.LogDownloads, name=TASK_LOG_VERSION_DOWNLOAD)
def log_version_download(version_id: int, timestamp: str):
    with transaction.atomic():
        PackageVersionDownloadEvent.objects.create(
            version_id=version_id,
            timestamp=datetime.fromisoformat(timestamp),
        )
        PackageVersion.objects.filter(id=version_id).update(
            downloads=F("downloads") + 1
        )

        transaction.on_commit(
            lambda: publish_event(
                KafkaTopics.METRICS_PACKAGES,
                key=PackageEvents.PACKAGE_DOWNLOADED,
                value={
                    "version_id": version_id,
                    "timestamp": timestamp,
                    "event_type": PackageEvents.PACKAGE_DOWNLOADED.value,
                },
            )
        )
