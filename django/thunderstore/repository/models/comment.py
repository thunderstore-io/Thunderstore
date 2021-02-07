from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from ulid2 import generate_ulid_as_uuid

from thunderstore.core.mixins import TimestampMixin


class Comment(TimestampMixin, models.Model):
    thread = GenericForeignKey("thread_content_type", "thread_object_id")
    thread_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    thread_object_id = models.PositiveIntegerField()
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
    )
    # author should never be NULL
    # It is temporarily set before the `User` `pre_delete` signal is ran but then set
    # to a "ghost user" `User`.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    content = models.TextField(
        max_length=2048,
    )
    uuid4 = models.UUIDField(
        default=generate_ulid_as_uuid,
        editable=False,
        unique=True,
        primary_key=True,
    )
    is_pinned = models.BooleanField(
        default=False,
    )
