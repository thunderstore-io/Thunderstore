import uuid

from django.conf import settings
from django.db import models


class Comment(models.Model):
    package = models.ForeignKey(
        "repository.Package",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    community = models.ForeignKey(
        "community.Community",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField(
        max_length=2048,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    date_updated = models.DateTimeField(
        auto_now=True,
    )
    uuid4 = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        primary_key=True,
    )
    is_pinned = models.BooleanField(
        default=False,
    )
