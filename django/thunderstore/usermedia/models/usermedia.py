import copy
from datetime import datetime
from typing import Optional

import ulid2
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum, sanitize_filename, sanitize_filepath
from thunderstore.usermedia.consts import MAX_UPLOAD_SIZE, MIN_UPLOAD_SIZE
from thunderstore.usermedia.exceptions import (
    UploadTooLargeException,
    UploadTooSmallException,
)


class UserMediaQueryset(models.QuerySet):
    def expired(self):
        return self.exclude(Q(expiry=None) | Q(expiry__gt=Now()))

    def active(self):
        return self.exclude(Q(expiry__lte=Now()))


class UserMediaStatus(ChoiceEnum):
    initial = "initial"
    upload_created = "upload_initiated"
    upload_error = "upload_error"
    upload_complete = "upload_complete"
    upload_aborted = "upload_aborted"


class UserMedia(TimestampMixin, models.Model):
    objects = UserMediaQueryset.as_manager()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="usermedia",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    filename = models.CharField(max_length=1024)
    key = models.CharField(max_length=2048)
    size = models.PositiveIntegerField()
    uuid = models.UUIDField(default=ulid2.generate_ulid_as_uuid, primary_key=True)

    # Prefix is the S3 storage bucket location prefix, only ever used for
    # building the file key (filepath in s3), which is what the rest of the
    # codebase should depend on.
    prefix = models.CharField(blank=True, null=True, max_length=256)

    expiry = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        default=UserMediaStatus.initial,
        choices=UserMediaStatus.as_choices(),
        max_length=64,
    )
    upload_id = models.TextField(blank=True, null=True)

    @classmethod
    def create_upload(
        cls,
        user: Optional[UserType],
        filename: str,
        size: int,
        expiry: Optional[datetime] = None,
    ) -> "UserMedia":
        if size > MAX_UPLOAD_SIZE:
            raise UploadTooLargeException(size, MAX_UPLOAD_SIZE)

        if size < MIN_UPLOAD_SIZE:
            raise UploadTooSmallException(size, MIN_UPLOAD_SIZE)

        user_media = UserMedia(
            uuid=ulid2.generate_ulid_as_uuid(),
            filename=sanitize_filename(filename),
            size=size,
            status=UserMediaStatus.initial,
            owner=user,
            prefix=sanitize_filepath(settings.USERMEDIA_S3_LOCATION),
            expiry=expiry,
        )
        user_media.key = user_media.compute_key()
        user_media.save()
        return user_media

    def compute_key(self) -> str:
        prefix = sanitize_filepath(self.prefix)
        filename = sanitize_filename(self.filename)
        return "/".join(
            [
                x
                for x in [
                    prefix,
                    "usermedia",
                    f"{self.uuid}-{filename}",
                ]
                if x
            ],
        )

    @property
    def s3_metadata(self):
        params = copy.deepcopy(settings.USERMEDIA_S3_OBJECT_PARAMETERS)
        params.update(
            {
                k: v
                for k, v in {
                    "UserMedia": str(self.uuid),
                    "Expiry": self.expiry.isoformat() if self.expiry else None,
                }.items()
                if v is not None
            },
        )
        return params

    @property
    def has_expired(self) -> bool:
        return bool(self.expiry and self.expiry <= timezone.now())

    def can_user_write(self, user: Optional[UserType]):
        return user == self.owner

    class Meta:
        verbose_name = "user media"
        verbose_name_plural = "user media"
