from thunderstore.ts_analytics.kafka import KafkaTopic, send_kafka_message


def format_datetime(date_or_string):
    if date_or_string is None:
        return None
    if isinstance(date_or_string, str):
        return date_or_string
    try:
        return date_or_string.isoformat()
    except AttributeError:
        return None


def package_version_download_event_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageVersionDownloadEvent post_save events.
    Sends download event information through Kafka as a Celery task.
    """
    if created:
        send_kafka_message(
            topic=KafkaTopic.PACKAGE_DOWNLOADED,
            payload={
                "id": instance.id,
                "version_id": instance.version_id,
                "timestamp": format_datetime(instance.timestamp),
            },
        )


def package_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Package post_save events.
    Sends package information through Kafka as a Celery task.
    """
    send_kafka_message(
        topic=KafkaTopic.PACKAGE_UPDATED,
        payload={
            "package_id": instance.id,
            "is_active": instance.is_active,
            "owner": instance.owner.name,
            "name": instance.name,
            "date_created": format_datetime(instance.date_created),
            "date_updated": format_datetime(instance.date_updated),
            "is_deprecated": instance.is_deprecated,
            "is_pinned": instance.is_pinned,
        },
    )


def package_version_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageVersion post_save events.
    Sends package version information through Kafka as a Celery task.
    """
    send_kafka_message(
        topic=KafkaTopic.PACKAGE_VERSION_UPDATED,
        payload={
            "id": instance.id,
            "is_active": instance.is_active,
            "owner": instance.package.owner.name,
            "name": instance.name,
            "version_number": instance.version_number,
            "package_id": instance.package_id,
            "downloads": instance.downloads,
            "date_created": format_datetime(instance.date_created),
            "file_size": instance.file_size,
        },
    )


def package_listing_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for PackageListing post_save events.
    Sends package listing information through Kafka as a Celery task.
    """
    send_kafka_message(
        topic=KafkaTopic.PACKAGE_LISTING_UPDATED,
        payload={
            "id": instance.id,
            "has_nsfw_content": instance.has_nsfw_content,
            "package_id": instance.package_id,
            "datetime_created": format_datetime(instance.datetime_created),
            "datetime_updated": format_datetime(instance.datetime_updated),
            "review_status": instance.review_status,
        },
    )


def community_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Community post_save events.
    Sends community information through Kafka as a Celery task.
    """
    send_kafka_message(
        topic=KafkaTopic.COMMUNITY_UPDATED,
        payload={
            "id": instance.id,
            "identifier": instance.identifier,
            "name": instance.name,
            "datetime_created": format_datetime(instance.datetime_created),
            "datetime_updated": format_datetime(instance.datetime_updated),
        },
    )
