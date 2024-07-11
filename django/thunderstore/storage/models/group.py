from typing import Optional

from django.db import models

from thunderstore.core.mixins import AdminLinkMixin, TimestampMixin
from thunderstore.storage.models.reference import DataBlobReference


class DataBlobGroup(TimestampMixin, AdminLinkMixin):
    """
    The DataBlobGroup class is intended to support grouping of multiple
    data blobs into logical groups, e.g. file trees. It does not hold much
    information itself, but acts as a common ID other objects can refer to.
    """

    name = models.TextField()
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def set_complete(self):
        self.is_complete = True
        self.save()

    def add_entry(
        self,
        data: bytes,
        name: str,
        *,
        content_type: Optional[str] = None,
        content_encoding: Optional[str] = None,
    ) -> "DataBlobReference":
        if self.is_complete:
            raise RuntimeError("Modifying complete groups is not permitted")

        return DataBlobReference.create(
            data,
            group=self,
            name=name,
            content_type=content_type,
            content_encoding=content_encoding,
        )
