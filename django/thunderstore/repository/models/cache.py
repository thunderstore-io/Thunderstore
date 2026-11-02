import gzip
import io
import json
import re
from datetime import timedelta
from itertools import chain
from typing import Any, Callable, Iterable, List, Optional

from django.contrib.postgres.expressions import ArraySubquery
from django.contrib.postgres.fields import ArrayField
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import (
    Count,
    DecimalField,
    F,
    Func,
    JSONField,
    OuterRef,
    QuerySet,
    Subquery,
    TextField,
    Value,
)
from django.db.models.functions import Cast, Coalesce, Concat, Lower
from django.utils import timezone

from thunderstore.community.models import Community, PackageListing
from thunderstore.core.mixins import S3FileMixin, SafeDeleteMixin
from thunderstore.repository.cache import (
    get_package_listing_base_queryset,
    order_package_listing_queryset,
)
from thunderstore.storage.models import DataBlob, DataBlobGroup
from thunderstore.utils.batch import batch


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

        listings_json = get_listing_json_queryset(community)

        for listing_ids in get_package_listing_ids(community):
            for listing_bytes in serialize_listing_chunk(listings_json, listing_ids):
                # Always add the first listing regardless of the size limit.
                if not chunk_content:
                    chunk_content.extend(listing_bytes)
                # Start new blob if adding current chunck would exceed the size limit.
                # +2 for opening and closing brackets
                elif (
                    len(chunk_content) + len(listing_bytes) + 2 > uncompressed_blob_size
                ):
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


def get_package_listing_ids(community: Community) -> Iterable[List[int]]:
    """
    Iterate over the PackageListing in chunks to limit the amount of
    data Django keeps in memory concurrently.
    """
    listing_ids = (
        order_package_listing_queryset(
            get_package_listing_base_queryset(community.identifier)
        )
        .values_list("id", flat=True)
        .iterator(chunk_size=1000)
    )

    yield from batch(1000, listing_ids)


class JSONBuildObject(Func):
    """
    Build a JSON object that keeps its keys in the order they're given.
    Django's JSONObject can't be used here because jsonb_build_object sorts the keys.
    """

    function = "JSON_BUILD_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields: Any) -> None:
        super().__init__(
            *chain.from_iterable(
                (Cast(Value(key), TextField()), value) for key, value in fields.items()
            )
        )


class IsoFormat(Func):
    """
    Format a timestamp the same way datetime.isoformat() does in UTC.
    isoformat() drops the fraction when it's zero, so we strip it here too.
    """

    template = (
        "replace(to_char((%(expressions)s) AT TIME ZONE 'UTC', "
        "'YYYY-MM-DD\"T\"HH24:MI:SS.US+00:00'), '.000000+', '+')"
    )
    output_field = TextField()


class VersionSortKey(Func):
    """
    Sort X.Y.Z version numbers numerically, eg. 1.10.0 comes after 1.9.0.
    Parts are cast to numeric because they can be larger than int.
    Anything other than digits and dots will fail the query. The version
    validators don't allow that anyway.
    """

    template = "string_to_array(%(expressions)s, '.')::numeric[]"
    output_field = ArrayField(DecimalField())


def _spliced_url(build_url: Callable[..., str], **parts: Any) -> Concat:
    """
    Build a URL in SQL from the model's own URL code instead of duplicating it here.
    build_url is called with a placeholder for each part. Each placeholder in the
    result is then swapped for that part's column.

    This only works for unsigned URLs where the parts don't need percent-encoding.
    Validated names and versions never do.
    """
    placeholders = {f"__{name}__": expression for name, expression in parts.items()}
    url = build_url(**{name: f"__{name}__" for name in parts})
    if "?" in url or any(placeholder not in url for placeholder in placeholders):
        raise ValueError(
            f"Expected each of {list(placeholders)} and no query in {url!r}"
        )
    tokens = re.split(f"({'|'.join(map(re.escape, placeholders))})", url)
    return Concat(
        *(placeholders[t] if t in placeholders else Value(t) for t in tokens if t)
    )


def get_listing_json_queryset(community: Community) -> QuerySet:
    """
    Build the JSON for each of the community's listings in Postgres, as (id, json) rows.
    The fields below are in the same order as the keys in the output.
    """
    from thunderstore.repository.models import (
        Package,
        PackageRating,
        PackageVersion,
        Team,
    )
    from thunderstore.repository.package_manifest import MAX_PACKAGE_DEPENDENCIES

    def package(owner: str, name: str) -> Package:
        return Package(owner=Team(name=owner), name=name)

    # full_package_name goes through "package" so it works on listings and versions.
    full_package_name = Concat("package__owner__name", Value("-"), "package__name")
    full_version_name = Concat(full_package_name, Value("-"), "version_number")

    # Use an isolated subquery for ratings to prevent massive joins
    ratings_subquery = Subquery(
        PackageRating.objects.filter(package_id=OuterRef("package_id"))
        .values("package_id")
        .annotate(count=Count("id"))
        .values("count")
    )

    dependency_names = (
        PackageVersion.objects.filter(dependants=OuterRef("pk"))
        .annotate(_full_name=full_version_name)
        .order_by(Lower("package__namespace__name"), Lower("package__name"))
        .values("_full_name")[:MAX_PACKAGE_DEPENDENCIES]
    )

    versions = (
        PackageVersion.objects.filter(package=OuterRef("package"), is_active=True)
        .order_by(VersionSortKey("version_number").desc())
        .values(
            json=JSONBuildObject(
                name=F("name"),
                full_name=full_version_name,
                description=F("description"),
                icon=_spliced_url(
                    lambda icon: PackageVersion(icon=icon).icon.url,
                    icon=F("icon"),
                ),
                version_number=F("version_number"),
                dependencies=ArraySubquery(dependency_names),
                download_url=_spliced_url(
                    lambda owner, name, version: PackageVersion(
                        package=package(owner, name), version_number=version
                    ).full_download_url,
                    owner=F("package__owner__name"),
                    name=F("package__name"),
                    version=F("version_number"),
                ),
                downloads=F("downloads"),
                date_created=IsoFormat("date_created"),
                website_url=F("website_url"),
                is_active=F("is_active"),
                uuid4=F("uuid4"),
                file_size=F("file_size"),
            )
        )
    )

    # Order by the through table's pk to keep categories in the order they were added.
    categories = (
        PackageListing.categories.through.objects.filter(packagelisting=OuterRef("pk"))
        .order_by("pk")
        .values("packagecategory__name")
    )

    listing = JSONBuildObject(
        name=F("package__name"),
        full_name=full_package_name,
        owner=F("package__owner__name"),
        package_url=_spliced_url(
            lambda owner, name: PackageListing(
                community=community, package=package(owner, name)
            ).get_full_url(),
            owner=F("package__owner__name"),
            name=F("package__name"),
        ),
        donation_link=F("package__owner__donation_link"),
        date_created=IsoFormat("package__date_created"),
        date_updated=IsoFormat("package__date_updated"),
        uuid4=F("package__uuid4"),
        rating_score=Coalesce(ratings_subquery, 0),
        is_pinned=F("package__is_pinned"),
        is_deprecated=F("package__is_deprecated"),
        has_nsfw_content=F("has_nsfw_content"),
        categories=ArraySubquery(categories),
        versions=ArraySubquery(versions),
    )

    return (
        PackageListing.objects.filter(community=community)
        .annotate(json=Cast(listing, TextField()))
        .values_list("id", "json")
    )


def serialize_listing_chunk(
    listings_json: QuerySet, listing_ids: List[int]
) -> Iterable[bytes]:
    """
    Yield each listing's JSON in the same order as listing_ids.
    Ids that no longer exist are skipped.
    """
    json_by_id = dict(listings_json.filter(id__in=listing_ids))
    for listing_id in listing_ids:
        if listing_id in json_by_id:
            yield json_by_id[listing_id].encode()


def get_index_blob(group: DataBlobGroup) -> DataBlob:
    chunk_urls: List[str] = [e.blob.data_url for e in group.entries.all()]
    index_content = gzip.compress(json.dumps(chunk_urls).encode(), mtime=0)
    return DataBlob.get_or_create(index_content)
