import json

from django.db import transaction

from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message
from thunderstore.ts_analytics.utils import format_datetime


def package_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Package post_save events.
    Sends package information through Kafka as a Celery task.
    """
    payload_string = json.dumps(
        {
            "package_id": instance.id,
            "is_active": instance.is_active,
            "owner": instance.owner.name,
            "name": instance.name,
            "date_created": format_datetime(instance.date_created),
            "date_updated": format_datetime(instance.date_updated),
            "is_deprecated": instance.is_deprecated,
            "is_pinned": instance.is_pinned,
        }
    )
    transaction.on_commit(
        lambda: send_kafka_message.delay(
            topic=KafkaTopic.PACKAGE_UPDATED,
            payload_string=payload_string,
        )
    )


def package_version_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageVersion post_save events.
    Sends package version information through Kafka as a Celery task.
    """
    payload_string = json.dumps(
        {
            "id": instance.id,
            "is_active": instance.is_active,
            "owner": instance.package.owner.name,
            "name": instance.name,
            "version_number": instance.version_number,
            "package_id": instance.package_id,
            "downloads": instance.downloads,
            "date_created": format_datetime(instance.date_created),
            "file_size": instance.file_size,
        }
    )
    transaction.on_commit(
        lambda: send_kafka_message.delay(
            topic=KafkaTopic.PACKAGE_VERSION_UPDATED,
            payload_string=payload_string,
        )
    )


def package_listing_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageListing post_save events.
    Sends package listing information through Kafka as a Celery task.
    """
    payload_string = json.dumps(
        {
            "id": instance.id,
            "has_nsfw_content": instance.has_nsfw_content,
            "package_id": instance.package_id,
            "datetime_created": format_datetime(instance.datetime_created),
            "datetime_updated": format_datetime(instance.datetime_updated),
            "review_status": instance.review_status,
        }
    )
    transaction.on_commit(
        lambda: send_kafka_message.delay(
            topic=KafkaTopic.PACKAGE_LISTING_UPDATED,
            payload_string=payload_string,
        )
    )


def community_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Community post_save events.
    Sends community information through Kafka as a Celery task.
    """
    payload_string = json.dumps(
        {
            "id": instance.id,
            "identifier": instance.identifier,
            "name": instance.name,
            "datetime_created": format_datetime(instance.datetime_created),
            "datetime_updated": format_datetime(instance.datetime_updated),
        }
    )
    transaction.on_commit(
        lambda: send_kafka_message.delay(
            topic=KafkaTopic.COMMUNITY_UPDATED, payload_string=payload_string
        )
    )
