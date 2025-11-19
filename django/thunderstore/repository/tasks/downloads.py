import json
from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.db.models import F

from thunderstore.core.settings import CeleryQueues
from thunderstore.metrics.models import PackageVersionDownloadEvent
from thunderstore.repository.models import PackageVersion
from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message
from thunderstore.ts_analytics.utils import format_datetime

TASK_LOG_VERSION_DOWNLOAD = "thunderstore.repository.tasks.log_version_download"


@shared_task(
    queue=CeleryQueues.LogDownloads,
    name=TASK_LOG_VERSION_DOWNLOAD,
    ignore_result=True,
)
def log_version_download(version_id: int, timestamp: str):
    with transaction.atomic():
        event = PackageVersionDownloadEvent.objects.create(
            version_id=version_id,
            timestamp=datetime.fromisoformat(timestamp),
        )
        PackageVersion.objects.filter(id=version_id).update(
            downloads=F("downloads") + 1
        )

        send_kafka_message(
            topic=KafkaTopic.PACKAGE_DOWNLOADED,
            payload_string=json.dumps(
                {
                    "id": event.id,
                    "version_id": version_id,
                    "timestamp": format_datetime(timestamp),
                }
            ),
        )
