from django.conf import settings
from django.contrib.auth.models import User as UserType
from django.core.exceptions import PermissionDenied
from django.db import models
from ulid2 import generate_ulid_as_uuid

from thunderstore.community.models import PackageListing
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.utils import capture_exception
from thunderstore.repository.models.thread import CommentsThreadMixin, Thread


class Comment(CommentsThreadMixin, TimestampMixin, models.Model):
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="comments",
    )
    content = models.TextField(
        max_length=2048,
    )
    uuid = models.UUIDField(
        primary_key=True,
        default=generate_ulid_as_uuid,
        editable=False,
    )
    is_pinned = models.BooleanField(
        default=False,
    )

    def ensure_can_edit_content(self, user: UserType) -> None:
        # Only the comment author can edit a comment's content
        if user != self.author:
            raise PermissionDenied("Only the comment author can edit a message")

    def ensure_can_pin(self, user: UserType) -> None:
        commented_object = self.thread.parent
        if isinstance(commented_object, PackageListing):
            # Must be a member of the identity to pin
            if not commented_object.package.owner.members.filter(
                user=user,
            ).exists():
                raise PermissionDenied("Must be a member to pin messages")
        elif isinstance(commented_object, Comment):
            # Use the parent's check
            # As nested comments are allowed, this could be another comment
            commented_object.ensure_can_pin(user)
        else:
            capture_exception(
                NotImplementedError(
                    (
                        "Comment pin permission logic not setup for "
                        f"{type(commented_object)}"
                    ),
                ),
            )
            raise PermissionDenied("Server error")
