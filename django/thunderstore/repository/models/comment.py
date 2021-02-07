from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
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


def _create_ghost_user_username(id_: str) -> str:
    return f"Ghost User {id_}"


def _create_ghost_user_email(id_: str) -> str:
    # The ID used in ghost user usernames and emails are not the same as their `User.id`
    # This is because `User` still uses an autoincrement ID
    return f"{id_}.gu@thunderstore.io"


@receiver(signals.pre_delete, sender=settings.AUTH_USER_MODEL)
def set_ghost_user(instance, **kwargs) -> None:
    if not instance.comments.exists():
        return
    uuid = generate_ulid_as_uuid()
    username = _create_ghost_user_username(uuid.hex)
    email = _create_ghost_user_email(uuid.hex)
    ghost_user = User.objects.create_user(username, email=email)
    for comment in instance.comments.iterator():
        comment.author = ghost_user
        comment.save()
