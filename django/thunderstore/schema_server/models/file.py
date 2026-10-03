import gzip
import io
from hashlib import sha256

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.db import models
from django.utils import timezone

from thunderstore.cache.utils import get_cache
from thunderstore.core.mixins import S3FileMixin

cache = get_cache("default")
CACHE_LOCK_TIMEOUT = 30


def get_schema_file_path(_, filename: str) -> str:
    return f"schema/sha256/{filename}"


class SchemaFile(S3FileMixin):
    data = models.FileField(
        upload_to=get_schema_file_path,
        storage=get_storage_class(settings.SCHEMA_FILE_STORAGE)(),
        editable=False,
        blank=True,
        null=True,
    )
    checksum_sha256 = models.CharField(
        max_length=512,
        editable=False,
        null=False,
        unique=True,
        db_index=True,
    )
    file_size = models.PositiveIntegerField()
    gzip_size = models.PositiveBigIntegerField()

    @classmethod
    def get_or_create(cls, content: bytes) -> "SchemaFile":
        hash = sha256()
        hash.update(content)
        checksum = hash.hexdigest()

        lock_key = f"lock.schemafile.{checksum}"
        with cache.lock(lock_key, timeout=CACHE_LOCK_TIMEOUT, blocking_timeout=None):
            if existing := cls.objects.filter(checksum_sha256=checksum).first():
                return existing

            gzipped = io.BytesIO()
            with gzip.GzipFile(fileobj=gzipped, mode="wb") as f:
                f.write(content)
            timestamp = timezone.now()

            file = ContentFile(
                # TODO: This is immediately passed to BytesIO again, meaning
                #       we're just wasting memory. Find a way to pass this to
                #       the Django model without the inefficiency.
                gzipped.getvalue(),
                name=f"{checksum}.json.gz",
            )

            return cls.objects.create(
                data=file,
                content_type="application/json",
                content_encoding="gzip",
                last_modified=timestamp,
                checksum_sha256=checksum,
                file_size=len(content),
                gzip_size=file.size,
            )
