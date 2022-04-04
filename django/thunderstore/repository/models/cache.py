import gzip
import io
from datetime import timedelta
from typing import Optional

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from thunderstore.cache.models import S3FileMixin
from thunderstore.community.models import Community


class APIV1PackageCache(S3FileMixin):
    community = models.ForeignKey(
        "community.Community",
        related_name="package_list_cache",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    @classmethod
    def get_latest_for_community(
        cls,
        community: Optional[Community] = None,
        community_identifier: Optional[str] = None,
    ) -> Optional["APIV1PackageCache"]:
        if community_identifier:
            return (
                APIV1PackageCache.objects.active()
                .filter(community__identifier=community_identifier)
                .order_by("-last_modified")
                .first()
            )
        elif community:
            return (
                APIV1PackageCache.objects.active()
                .filter(community=community)
                .order_by("-last_modified")
                .first()
            )
        else:
            return None

    @classmethod
    def update_for_community(
        cls, community: Community, content: bytes
    ) -> "APIV1PackageCache":
        gzipped = io.BytesIO()
        with gzip.GzipFile(fileobj=gzipped, mode="wb") as f:
            f.write(content)
        timestamp = timezone.now()
        file = ContentFile(
            # TODO: This is immediately passed to BytesIO again, meaning
            #       we're just wasting memory. Find a way to pass this to
            #       the Django model without the inefficiency.
            gzipped.getvalue(),
            name=f"{timestamp.isoformat()}-{community.identifier}.json.gz",
        )
        return cls.objects.create(
            community=community,
            data=file,
            content_type="application/json",
            content_encoding="gzip",
            last_modified=timestamp,
        )

    @classmethod
    def drop_stale_cache(cls):
        for community in Community.objects.all().iterator():
            latest = cls.get_latest_for_community(community)
            cutoff = latest.last_modified - timedelta(hours=1)
            stale = cls.objects.filter(last_modified__lte=cutoff, community=community)
            for entry in stale.iterator():
                entry.delete()
        for entry in cls.objects.filter(community=None).iterator():
            entry.delete()
