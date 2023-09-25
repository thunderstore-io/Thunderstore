from hashlib import sha256
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.db import models

from thunderstore.core.mixins import SafeDeleteMixin, TimestampMixin


def get_object_file_path(_, filename: str) -> str:
    return f"blob-storage/sha256/{filename}.sha256.blob"


class DataBlob(SafeDeleteMixin):
    """
    The DataBlob class is responsible for storing arbitrary blobs of data with
    automatic deduplication by blob sha256 checksum. It is not interested in
    any metadata which is not inferable without parsing the data. Additional
    meta is left for DataBlobReference, which is also interested in contextual
    information.
    """

    data = models.FileField(
        upload_to=get_object_file_path,
        storage=get_storage_class(settings.BLOB_FILE_STORAGE)(),
        editable=False,
        blank=True,
        null=True,
    )
    data_size = models.BigIntegerField()
    checksum_sha256 = models.CharField(
        max_length=512,
        editable=False,
        null=False,
        unique=True,
        db_index=True,
    )

    @property
    def data_url(self) -> str:
        return self.data.url

    @classmethod
    def get_or_create(cls, content: bytes) -> "DataBlob":
        # TODO: Add support for streamable input
        hash = sha256()
        hash.update(content)
        checksum = hash.hexdigest()

        if existing := cls.objects.filter(checksum_sha256=checksum).first():
            return existing

        file = ContentFile(content, name=f"{checksum}.sha256.blob")
        return cls.objects.create(
            data=file,
            checksum_sha256=checksum,
            data_size=len(content),
        )

    def on_safe_delete(self):
        self.data.delete()


class DataBlobReferenceManager(models.Manager):
    """
    Automatically applies appropriate select_related to DataBlobReference
    querysets.
    """

    def get_queryset(self):
        return super().get_queryset().select_related("blob")


class DataBlobReference(TimestampMixin):
    """
    Acts as a middle man between DataBlob and the consumers of DataBlob, and
    is responsible for storing contextual use-case dependant information (such
    as timestamps which apply only for that use case). The reference can be
    treated as a handle/pointer which can be updated to point to different
    blobs if the use case needs to "overwrite" the current data.
    """

    blob: DataBlob = models.ForeignKey(
        "storage.DataBlob",
        related_name="references",
        on_delete=models.PROTECT,
    )
    objects: "models.Manager[DataBlobReference]" = DataBlobReferenceManager()

    @property
    def data_size(self) -> int:
        return self.blob.data_size

    @property
    def data_url(self) -> str:
        return self.blob.data_url

    @property
    def data_checksum_sha256(self) -> str:
        return self.blob.checksum_sha256

    # Speculative fields based on what meta might be needed by consumers
    name = models.TextField(blank=True, null=True)
    content_type = models.TextField(blank=True, null=True)
    content_encoding = models.TextField(blank=True, null=True)

    @property
    def data(self) -> bytes:
        # TODO: Add support for streamable output
        return self.blob.data.read()

    @data.setter
    def data(self, data: bytes):
        # TODO: Add support for streamable input
        self.blob = DataBlob.get_or_create(data)

    @classmethod
    def create(
        cls,
        data: bytes,
        *,
        name: Optional[str] = None,
        content_type: Optional[str] = None,
        content_encoding: Optional[str] = None,
    ) -> "DataBlobReference":
        # TODO: Add support for streamable input
        blob = DataBlob.get_or_create(data)
        return cls.objects.create(
            blob=blob,
            name=name,
            content_type=content_type,
            content_encoding=content_encoding,
        )
