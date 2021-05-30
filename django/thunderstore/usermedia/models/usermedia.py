import copy

import ulid2
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum


class UserMediaQueryset(models.QuerySet):
    def expired(self):
        return self.exclude(Q(expiry=None) | Q(expiry__gt=timezone.now()))

    def active(self):
        return self.exclude(Q(expiry__lte=timezone.now()))


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
    prefix = models.CharField(blank=True, null=True, max_length=256)
    expiry = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        default=UserMediaStatus.initial,
        choices=UserMediaStatus.as_choices(),
        max_length=64,
    )
    upload_id = models.TextField(blank=True, null=True)

    def compute_key(self) -> str:
        return "/".join(
            [
                x
                for x in [
                    self.prefix,
                    "usermedia",
                    f"{self.uuid}-{self.filename}",
                ]
                if x is not None
            ]
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
            }
        )
        return params

    def can_user_write(self, user: UserType):
        return user == self.owner

    class Meta:
        verbose_name = "user media"
        verbose_name_plural = "user media"
