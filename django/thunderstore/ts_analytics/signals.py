from django.db import transaction

from thunderstore.ts_analytics.kafka import KafkaTopic, send_kafka_message_async


def package_version_download_event_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageVersionDownloadEvent post_save events.
    Sends download event information through Kafka as a Celery task.
    """
    if created:
        transaction.on_commit(
            lambda: send_kafka_message_async.delay(
                topic=KafkaTopic.PACKAGE_DOWNLOADED,
                payload={
                    "id": instance.id,
                    "version_id": instance.version_id,
                    "timestamp": instance.timestamp.isoformat(),
                },
            )
        )


def package_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Package post_save events.
    Sends package information through Kafka as a Celery task.
    """
    transaction.on_commit(
        lambda: send_kafka_message_async.delay(
            topic=KafkaTopic.PACKAGE_UPDATED,
            payload={
                "package_id": instance.id,
                "is_active": instance.is_active,
                "owner": instance.owner.name,
                "name": instance.name,
                "date_created": instance.date_created.isoformat(),
                "date_updated": instance.date_updated.isoformat(),
                "is_deprecated": instance.is_deprecated,
                "is_pinned": instance.is_pinned,
            },
        )
    )


def package_version_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageVersion post_save events.
    Sends package version information through Kafka as a Celery task.
    """
    transaction.on_commit(
        lambda: send_kafka_message_async.delay(
            topic=KafkaTopic.PACKAGE_VERSION_UPDATED,
            payload={
                "id": instance.id,
                "is_active": instance.is_active,
                "owner": instance.package.owner.name,
                "name": instance.name,
                "version_number": instance.version_number,
                "package_id": instance.package_id,
                "downloads": instance.downloads,
                "date_created": instance.date_created.isoformat(),
                "file_size": instance.file_size,
            },
        )
    )


def package_listing_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageListing post_save events.
    Sends package listing information through Kafka as a Celery task.
    """
    transaction.on_commit(
        lambda: send_kafka_message_async.delay(
            topic=KafkaTopic.PACKAGE_LISTING_UPDATED,
            payload={
                "id": instance.id,
                "has_nsfw_content": instance.has_nsfw_content,
                "package_id": instance.package_id,
                "datetime_created": instance.datetime_created.isoformat(),
                "datetime_updated": instance.datetime_updated.isoformat(),
                "review_status": instance.review_status,
            },
        )
    )


def community_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Community post_save events.
    Sends community information through Kafka as a Celery task.
    """
    transaction.on_commit(
        lambda: send_kafka_message_async.delay(
            topic=KafkaTopic.COMMUNITY_UPDATED,
            payload={
                "id": instance.id,
                "identifier": instance.identifier,
                "name": instance.name,
                "datetime_created": instance.datetime_created.isoformat(),
                "datetime_updated": instance.datetime_updated.isoformat(),
            },
        )
    )
