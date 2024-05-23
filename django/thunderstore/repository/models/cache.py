import gzip
import io
import json
from datetime import timedelta
from typing import Any, List, Optional

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from thunderstore.community.models import Community, PackageListing
from thunderstore.core.mixins import S3FileMixin, SafeDeleteMixin
from thunderstore.repository.cache import (
    get_package_listing_queryset,
    order_package_listing_queryset,
)
from thunderstore.storage.models import DataBlob, DataBlobGroup


class APIExperimentalPackageIndexCache(S3FileMixin):
    @classmethod
    def get_latest(cls) -> Optional["APIExperimentalPackageIndexCache"]:
        return cls.objects.active().order_by("-last_modified").first()

    @classmethod
    def update(cls, content: bytes) -> "APIExperimentalPackageIndexCache":
        gzipped = io.BytesIO()
        with gzip.GzipFile(fileobj=gzipped, mode="wb") as f:
            f.write(content)
        timestamp = timezone.now()
        file = ContentFile(
            # TODO: This is immediately passed to BytesIO again, meaning
            #       we're just wasting memory. Find a way to pass this to
            #       the Django model without the inefficiency.
            gzipped.getvalue(),
            name=f"full-index-{timestamp.isoformat()}.json.gz",
        )
        return cls.objects.create(
            data=file,
            content_type="application/json",
            content_encoding="gzip",
            last_modified=timestamp,
        )

    @classmethod
    def drop_stale_cache(cls):
        latest = cls.get_latest()
        if latest is None:
            return
        # We don't immediately delete the old files as doing so will also
        # remove them from the CDN, and there might still be active use
        # for them due to other levels of caching.
        cutoff = latest.last_modified - timedelta(hours=3)
        stale = cls.objects.filter(last_modified__lte=cutoff)
        for entry in stale.iterator():
            entry.delete()


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
        community_identifier: Optional[str] = None,
    ) -> Optional["APIV1PackageCache"]:
        if community_identifier:
            return (
                APIV1PackageCache.objects.active()
                .filter(community__identifier=community_identifier)
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
            latest = cls.get_latest_for_community(
                community_identifier=community.identifier
            )
            if latest is None:
                continue
            cutoff = latest.last_modified - timedelta(hours=1)
            stale = cls.objects.filter(last_modified__lte=cutoff, community=community)
            for entry in stale.iterator():
                entry.delete()
        for entry in cls.objects.filter(community=None).iterator():
            entry.delete()


class APIV1ChunkedPackageCache(SafeDeleteMixin):
    community: Community = models.ForeignKey(
        "community.Community",
        related_name="chunked_package_list_cache",
        on_delete=models.CASCADE,
    )
    index: DataBlob = models.ForeignKey(
        "storage.DataBlob",
        related_name="chunked_package_indexes",
        on_delete=models.PROTECT,
    )
    chunks: DataBlobGroup = models.ForeignKey(
        "storage.DataBlobGroup",
        related_name="chunked_package_list_cache",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = "created_at"

    CACHE_CUTOFF_HOURS = 3
    UNCOMPRESSED_CHUNK_LIMIT = 14000000  # 14MB compresses into ~1MB files.

    @classmethod
    def get_latest_for_community(
        cls,
        community: Community,
    ) -> Optional["APIV1ChunkedPackageCache"]:
        try:
            return cls.objects.filter(community=community.pk).latest()
        except APIV1ChunkedPackageCache.DoesNotExist:
            return None

    @classmethod
    def update_for_community(
        cls,
        community: Community,
        chunk_size_limit: Optional[int] = None,
    ) -> None:
        """
        Chunk community's PackageListings into blob files and create an
        index blob that points to URLs of the chunks.
        """
        uncompressed_blob_size = chunk_size_limit or cls.UNCOMPRESSED_CHUNK_LIMIT
        group = DataBlobGroup.objects.create(
            name=f"Chunked package list: {community.identifier}",
        )
        chunk_content = bytearray()

        def finalize_blob() -> None:
            group.add_entry(
                gzip.compress(b"[" + chunk_content + b"]", mtime=0),
                name=f"Package list chunk for {community.identifier}",
                content_type="application/json",
                content_encoding="gzip",
            )

        for listing in get_package_listings(community):
            listing_bytes = listing_to_json(listing)

            # Always add the first listing regardless of the size limit.
            if not chunk_content:
                chunk_content.extend(listing_bytes)
            # Start new blob if adding current chunck would exceed the size limit.
            # +2 for opening and closing brackets
            elif len(chunk_content) + len(listing_bytes) + 2 > uncompressed_blob_size:
                finalize_blob()
                chunk_content = bytearray(listing_bytes)
            else:
                chunk_content.extend(b"," + listing_bytes)

        if len(chunk_content) or not group.entries.exists():
            finalize_blob()

        group.set_complete()
        index = get_index_blob(group)
        cls.objects.create(community=community, index=index, chunks=group)

    @classmethod
    def drop_stale_cache(cls) -> None:
        """
        Delete objects from database and blob files from S3 buckets.
        Cutoff period is used to ensure blobs still referenced by
        cached data is not dropped prematurely.

        TODO: only soft deletes the parent object until we've figured
        # out how to safely delete the blobs from the main and mirror
        # storages. When the hard deletes are implemented, acknowledge
        # that identical (e.g. empty) index/package chunk blobs are
        # shared between the caches. Therefore a blob can't be deleted
        # just because it's no longer used by *a* cache.
        """
        for community in Community.objects.iterator():
            latest = cls.get_latest_for_community(community)
            if latest is None:
                continue

            cutoff = latest.created_at - timedelta(hours=cls.CACHE_CUTOFF_HOURS)
            cls.objects.filter(created_at__lte=cutoff, community=community).update(
                is_deleted=True,
            )

    @classmethod
    def get_blob_content(cls, blob: DataBlob) -> List[Any]:
        """
        QoL method for returning the content of either index or chunk blob.
        """
        with gzip.open(blob.data, "rb") as f:
            return json.loads(f.read())


def get_package_listings(community: Community) -> models.QuerySet["PackageListing"]:
    listing_ids = get_package_listing_queryset(community.identifier).values_list(
        "id",
        flat=True,
    )
    listing_ref = PackageListing.objects.filter(pk=models.OuterRef("pk"))

    return order_package_listing_queryset(
        PackageListing.objects.filter(id__in=listing_ids)
        .select_related("community", "package", "package__owner")
        .prefetch_related("categories", "community__sites", "package__versions")
        .annotate(
            _rating_score=models.Subquery(
                listing_ref.annotate(
                    ratings=models.Count("package__package_ratings"),
                ).values("ratings"),
            ),
        ),
    )


def listing_to_json(listing: PackageListing) -> bytes:
    return json.dumps(
        {
            "name": listing.package.name,
            "full_name": listing.package.full_package_name,
            "owner": listing.package.owner.name,
            "package_url": listing.get_full_url(),
            "donation_link": listing.package.owner.donation_link,
            "date_created": listing.package.date_created.isoformat(),
            "date_updated": listing.package.date_updated.isoformat(),
            "uuid4": str(listing.package.uuid4),
            "rating_score": listing.rating_score,
            "is_pinned": listing.package.is_pinned,
            "is_deprecated": listing.package.is_deprecated,
            "has_nsfw_content": listing.has_nsfw_content,
            "categories": [c.name for c in listing.categories.all()],
            # TODO: god-awful performance from OVER NINE THOUSAAAAND database hits
            "versions": [
                {
                    "name": version.name,
                    "full_name": version.full_version_name,
                    "description": version.description,
                    "icon": version.icon.url,
                    "version_number": version.version_number,
                    "dependencies": [
                        d.full_version_name for d in version.dependencies.all()
                    ],
                    "download_url": version.full_download_url,
                    "downloads": version.downloads,
                    "date_created": version.date_created.isoformat(),
                    "website_url": version.website_url,
                    # TODO: what is this needed for, inactive ones have been filtered out anyway?
                    "is_active": version.is_active,
                    "uuid4": str(version.uuid4),
                    "file_size": version.file_size,
                }
                for version in listing.package.available_versions
            ],
        },
    ).encode()


def get_index_blob(group: DataBlobGroup) -> DataBlob:
    chunk_urls: List[str] = [e.blob.data_url for e in group.entries.all()]
    index_content = gzip.compress(json.dumps(chunk_urls).encode(), mtime=0)
    return DataBlob.get_or_create(index_content)
