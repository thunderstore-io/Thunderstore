from datetime import datetime
from typing import List

from django.db import transaction
from pydantic import BaseModel

from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.models import Package, PackageVersion
from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message


def _send_kafka_message_on_commit(topic: str, payload: BaseModel):
    transaction.on_commit(
        lambda: send_kafka_message.delay(topic=topic, payload_string=payload.json())
    )


class AnalyticsEventPackageUpdate(BaseModel):
    id: int
    is_active: bool
    owner__id: int
    owner__name: str
    namespace__name: str
    name: str
    full_package_name: str
    date_created: datetime
    date_updated: datetime
    is_deprecated: bool


def package_post_save(sender, instance: Package, created, **kwargs):
    payload = AnalyticsEventPackageUpdate(
        id=instance.pk,
        is_active=instance.is_active,
        owner__id=instance.owner.pk,
        owner__name=instance.owner.name,
        namespace__name=instance.namespace.name,
        name=instance.name,
        full_package_name=instance.full_package_name,
        date_created=instance.date_created,
        date_updated=instance.date_updated,
        is_deprecated=instance.is_deprecated,
    )
    _send_kafka_message_on_commit(KafkaTopic.M_PACKAGE_UPDATE_V1, payload)


class AnalyticsEventPackageVersionUpdate(BaseModel):
    id: int
    is_active: bool
    owner__id: int
    owner__name: str
    namespace__name: str
    name: str
    full_version_name: str
    version_number: str
    package__id: int
    date_created: datetime
    file_size: int


def package_version_post_save(sender, instance: PackageVersion, created, **kwargs):
    payload = AnalyticsEventPackageVersionUpdate(
        id=instance.pk,
        is_active=instance.is_active,
        owner__id=instance.owner.pk,
        owner__name=instance.owner.name,
        namespace__name=instance.namespace.name,
        name=instance.name,
        full_version_name=instance.full_version_name,
        version_number=instance.version_number,
        package__id=instance.package.pk,
        date_created=instance.date_created,
        file_size=instance.file_size,
    )
    _send_kafka_message_on_commit(KafkaTopic.M_PACKAGE_VERSION_UPDATE_V1, payload)


class AnalyticsEventPackageListingUpdate(BaseModel):
    id: int
    has_nsfw_content: bool
    package__id: int
    community__id: int
    community__identifier: str
    categories__slug: List[str]
    datetime_created: datetime
    datetime_updated: datetime
    review_status: str


def package_listing_post_save(sender, instance: PackageListing, created, **kwargs):
    payload = AnalyticsEventPackageListingUpdate(
        id=instance.pk,
        has_nsfw_content=instance.has_nsfw_content,
        package__id=instance.package.pk,
        community__id=instance.community.id,
        community__identifier=instance.community.identifier,
        categories__slug=list(instance.categories.values_list("slug", flat=True)),
        datetime_created=instance.datetime_created,
        datetime_updated=instance.datetime_updated,
        review_status=instance.review_status,
    )
    _send_kafka_message_on_commit(KafkaTopic.M_PACKAGE_LISTING_UPDATE_V1, payload)


class AnalyticsEventCommunityUpdate(BaseModel):
    id: int
    identifier: str
    name: str
    datetime_created: datetime
    datetime_updated: datetime


def community_post_save(sender, instance: Community, created, **kwargs):
    payload = AnalyticsEventCommunityUpdate(
        id=instance.pk,
        identifier=instance.identifier,
        name=instance.name,
        datetime_created=instance.datetime_created,
        datetime_updated=instance.datetime_updated,
    )
    _send_kafka_message_on_commit(KafkaTopic.M_COMMUNITY_UPDATE_V1, payload)
