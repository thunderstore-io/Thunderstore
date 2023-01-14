from typing import Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files import File
from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.ipfs.models import IPFSObject, IPFSObjectRelationMixin


class SchemaChannel(TimestampMixin):
    objects: Manager["SchemaChannel"]

    identifier = models.SlugField(max_length=128, unique=True)
    authorized_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="schema_channels"
    )
    latest = models.ForeignKey(
        "schema_server.SchemaChannelFile",
        related_name="+",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        if self.pk:
            in_db = type(self).objects.get(pk=self.pk)
            if in_db.identifier != self.identifier:
                raise ValidationError("Field 'identifier' is read only")
        return super().save(*args, **kwargs)

    @classmethod
    def update_channel(
        cls, user: Optional[UserType], identifier: str, content: bytes
    ) -> "SchemaChannelFile":
        channel = SchemaChannel.objects.get(identifier=identifier)
        if (
            user is None
            or not user.is_active
            or user not in channel.authorized_users.all()
        ):
            raise PermissionDenied()
        return channel.add_new_version(content)

    def add_new_version(self, content: bytes) -> "SchemaChannelFile":
        self.latest = SchemaChannelVersion.create(self, content)
        self.save()
        return self.latest

    def __str__(self):
        return self.identifier


class SchemaChannelVersion(IPFSObjectRelationMixin, TimestampMixin):
    channel = models.ForeignKey(
        "schema_server.SchemaChannel",
        related_name="channel_files",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)

    @classmethod
    def create(cls, channel: SchemaChannel, content: File):
        return cls.objects.create(
            ipfs_object=IPFSObject.objects.get_or_create_for_file(content),
            channel=channel,
        )

    def __str__(self):
        return f"{self.channel} {self.datetime_created.isoformat()}"
