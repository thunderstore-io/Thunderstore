from hashlib import sha256

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.db import models

from thunderstore.core.mixins import SafeDeleteMixin


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

    def __str__(self):
        return self.checksum_sha256

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
