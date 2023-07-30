from typing import Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType
from thunderstore.schema_server.models.file import SchemaFile


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
        channel: SchemaChannel = SchemaChannel.objects.get(identifier=identifier)
        if (
            user is None
            or not user.is_active
            or user not in channel.authorized_users.all()
        ):
            raise PermissionDenied()
        return channel._add_new_version(content)

    def _add_new_version(self, content: bytes) -> "SchemaChannelFile":
        self.latest = SchemaChannelFile._create_version(self, content)
        self.save()
        return self.latest

    def __str__(self):
        return self.identifier


class SchemaChannelFile(TimestampMixin):
    channel = models.ForeignKey(
        "schema_server.SchemaChannel",
        related_name="channel_files",
        on_delete=models.CASCADE,
    )
    file = models.ForeignKey(
        "schema_server.SchemaFile",
        related_name="channel_files",
        on_delete=models.PROTECT,
    )
    is_active = models.BooleanField(default=True)

    @classmethod
    def _create_version(cls, channel: SchemaChannel, content: bytes):
        """
        This method should only be called internally by SchemaChannel
        """

        return cls.objects.create(
            channel=channel,
            file=SchemaFile.get_or_create(content),
        )

    def __str__(self):
        return f"{self.datetime_created.isoformat()} {self.file.checksum_sha256}"
