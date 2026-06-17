import gzip
import io
import json
from datetime import timedelta
from functools import lru_cache
from typing import Any, Iterable, List, Optional, Tuple

from django.core.files.base import ContentFile
from django.db import connection, models
from django.utils import timezone

from thunderstore.community.models import Community, PackageListing  # noqa: F401
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

        url_templates = _community_url_templates(community)

        for listing_ids in get_package_listing_ids(community):
            for listing_bytes in serialize_listing_chunk(url_templates, listing_ids):
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


def get_index_blob(group: DataBlobGroup) -> DataBlob:
    chunk_urls: List[str] = [e.blob.data_url for e in group.entries.all()]
    index_content = gzip.compress(json.dumps(chunk_urls).encode(), mtime=0)
    return DataBlob.get_or_create(index_content)


# URL-safe sentinels absent from owner/package/version values, so SQL replace() is unambiguous.
_OWNER, _NAME, _VERSION, _ICON = "~owner~", "~name~", "~version~", "~icon~"


def _community_url_templates(community: Community) -> dict:
    """URL/icon templates carrying sentinels the chunk SQL fills in per row."""
    from django.conf import settings
    from django.urls import reverse

    from thunderstore.frontend.url_reverse import get_community_url_reverse_args
    from thunderstore.repository.models import PackageVersion

    site = community.main_site
    hostname = settings.PRIMARY_HOST if site is None else site.site.domain
    return {
        "package_url": settings.PROTOCOL
        + hostname
        + reverse(
            **get_community_url_reverse_args(
                community, "packages.detail", {"owner": _OWNER, "name": _NAME}
            )
        ),
        "download_url": settings.PROTOCOL
        + settings.PRIMARY_HOST
        + reverse(
            "old_urls:packages.download",
            kwargs={"owner": _OWNER, "name": _NAME, "version": _VERSION},
        ),
        "icon": PackageVersion._meta.get_field("icon").storage.url(_ICON),
    }


def _json_object(fields: List[Tuple[str, str]]) -> str:
    """Render (json_key, sql_expr) pairs into json_build_object(). Arg order is the
    emitted JSON key order."""
    args = ", ".join(f"'{key}', {expr}" for key, expr in fields)
    return f"json_build_object({args})"


@lru_cache(maxsize=1)
def _chunk_sql() -> str:
    """Build a chunk's listing JSON in Postgres. _listing_fields/_version_fields
    are the sole declaration of the index's fields and key order."""
    from thunderstore.community.models import PackageCategory, PackageListing
    from thunderstore.repository.models import (
        Namespace,
        Package,
        PackageRating,
        PackageVersion,
        Team,
    )

    def tb(m):
        return m._meta.db_table

    def co(m, f):
        return m._meta.get_field(f).column

    def pkc(m):
        return m._meta.pk.column

    def m2m_cols(model, field_name):
        # Through-table (table, pk, from_col, to_col) via Django's m2m field-name API.
        field = model._meta.get_field(field_name)
        through = field.remote_field.through._meta
        from_col = through.get_field(field.m2m_field_name()).column
        to_col = through.get_field(field.m2m_reverse_field_name()).column
        return through.db_table, through.pk.column, from_col, to_col

    cat_table, _, cat_from, cat_to = m2m_cols(PackageListing, "categories")
    dep_table, _, dep_from, dep_to = m2m_cols(PackageVersion, "dependencies")

    def iso(col):
        # Match datetime.isoformat(): 6-digit fraction, dropped when zero.
        b = f"{col} AT TIME ZONE 'UTC'"
        full = "'YYYY-MM-DD\"T\"HH24:MI:SS.US+00:00'"
        secs = "'YYYY-MM-DD\"T\"HH24:MI:SS+00:00'"
        return (
            f"CASE WHEN to_char({b}, 'US') = '000000' "
            f"THEN to_char({b}, {secs}) ELSE to_char({b}, {full}) END"
        )

    # Order deps by namespace then package name (lowercased), matching the
    # chunked index path from #1319. Unfiltered by is_active, like dependencies.all().
    deps = f"""COALESCE((
        SELECT json_agg(
            downer.name || '-' || dpkg.name || '-' || dv.version_number
            ORDER BY lower(dns.name), lower(dpkg.name)
        )
        FROM {dep_table} pvd
        JOIN {tb(PackageVersion)} dv ON dv.{pkc(PackageVersion)} = pvd.{dep_to}
        JOIN {tb(Package)} dpkg ON dpkg.{pkc(Package)} = dv.{co(PackageVersion, 'package')}
        JOIN {tb(Team)} downer ON downer.{pkc(Team)} = dpkg.{co(Package, 'owner')}
        JOIN {tb(Namespace)} dns ON dns.{pkc(Namespace)} = dpkg.{co(Package, 'namespace')}
        WHERE pvd.{dep_from} = v.{pkc(PackageVersion)}
    ), '[]'::json)"""

    download_url = (
        f"replace(replace(replace(%(download_url)s, "
        f"'{_OWNER}', owner.name), '{_NAME}', pkg.name), '{_VERSION}', v.version_number)"
    )

    _version_fields = [
        ("name", "v.name"),
        ("full_name", "owner.name || '-' || pkg.name || '-' || v.version_number"),
        ("description", "v.description"),
        ("icon", f"replace(%(icon)s, '{_ICON}', v.icon)"),
        ("version_number", "v.version_number"),
        ("dependencies", deps),
        ("download_url", download_url),
        ("downloads", "v.downloads"),
        ("date_created", iso("v.date_created")),
        ("website_url", "v.website_url"),
        ("is_active", "v.is_active"),
        ("uuid4", "v.uuid4"),
        ("file_size", "v.file_size"),
    ]
    version_obj = _json_object(_version_fields)

    # Semver order: version_number is validated X.Y.Z, so a numeric component sort is total.
    versions = f"""COALESCE((
        SELECT json_agg(s.obj ORDER BY s.v1 DESC, s.v2 DESC, s.v3 DESC)
        FROM (
            SELECT {version_obj} AS obj,
                split_part(v.version_number, '.', 1)::numeric AS v1,
                split_part(v.version_number, '.', 2)::numeric AS v2,
                split_part(v.version_number, '.', 3)::numeric AS v3
            FROM {tb(PackageVersion)} v
            WHERE v.{co(PackageVersion, 'package')} = pkg.{pkc(Package)} AND v.is_active
        ) s
    ), '[]'::json)"""

    categories = f"""COALESCE((
        SELECT json_agg(cat.name ORDER BY cat.name)
        FROM {cat_table} lc
        JOIN {tb(PackageCategory)} cat ON cat.{pkc(PackageCategory)} = lc.{cat_to}
        WHERE lc.{cat_from} = pl.{pkc(PackageListing)}
    ), '[]'::json)"""

    rating = (
        f"(SELECT count(*) FROM {tb(PackageRating)} r "
        f"WHERE r.{co(PackageRating, 'package')} = pkg.{pkc(Package)})"
    )

    package_url = f"replace(replace(%(package_url)s, '{_OWNER}', owner.name), '{_NAME}', pkg.name)"

    _listing_fields = [
        ("name", "pkg.name"),
        ("full_name", "owner.name || '-' || pkg.name"),
        ("owner", "owner.name"),
        ("package_url", package_url),
        ("donation_link", "owner.donation_link"),
        ("date_created", iso("pkg.date_created")),
        ("date_updated", iso("pkg.date_updated")),
        ("uuid4", "pkg.uuid4"),
        ("rating_score", rating),
        ("is_pinned", "pkg.is_pinned"),
        ("is_deprecated", "pkg.is_deprecated"),
        ("has_nsfw_content", "pl.has_nsfw_content"),
        ("categories", categories),
        ("versions", versions),
    ]
    return f"""
    SELECT ({_json_object(_listing_fields)})::text
    FROM unnest(%(ids)s::int[]) WITH ORDINALITY AS req(id, ord)
    JOIN {tb(PackageListing)} pl ON pl.{pkc(PackageListing)} = req.id
    JOIN {tb(Package)} pkg ON pkg.{pkc(Package)} = pl.{co(PackageListing, 'package')}
    JOIN {tb(Team)} owner ON owner.{pkc(Team)} = pkg.{co(Package, 'owner')}
    ORDER BY req.ord
    """


def serialize_listing_chunk(
    url_templates: dict, listing_ids: List[int]
) -> Iterable[bytes]:
    """Yield each listing's JSON in listing_ids order, built in Postgres so no ORM
    objects are hydrated for the chunk."""
    ids = list(listing_ids)
    if not ids:
        return
    params = {**url_templates, "ids": ids}
    with connection.cursor() as cursor:
        cursor.execute(_chunk_sql(), params)
        for (listing_json,) in cursor:
            yield listing_json.encode()
