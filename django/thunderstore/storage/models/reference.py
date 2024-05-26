from typing import TYPE_CHECKING, Optional

from django.db import models

from thunderstore.core.mixins import AdminMixin, TimestampMixin
from thunderstore.storage.models.blob import DataBlob

if TYPE_CHECKING:
    from thunderstore.storage.models.group import DataBlobGroup


class DataBlobReferenceManager(models.Manager):
    """
    Automatically applies appropriate select_related to DataBlobReference
    querysets.
    """

    def get_queryset(self):
        return super().get_queryset().select_related("blob")


class DataBlobReference(TimestampMixin, AdminMixin):
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
    group: Optional["DataBlobGroup"] = models.ForeignKey(
        "storage.DataBlobGroup",
        related_name="entries",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    objects: "models.Manager[DataBlobReference]" = DataBlobReferenceManager()

    def __str__(self):
        return self.name

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
        group: Optional["DataBlobGroup"] = None,
        name: Optional[str] = None,
        content_type: Optional[str] = None,
        content_encoding: Optional[str] = None,
    ) -> "DataBlobReference":
        # TODO: Add support for streamable input
        blob = DataBlob.get_or_create(data)
        return cls.objects.create(
            blob=blob,
            group=group,
            name=name,
            content_type=content_type,
            content_encoding=content_encoding,
        )
