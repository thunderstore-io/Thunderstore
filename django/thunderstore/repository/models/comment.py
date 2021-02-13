from django.conf import settings
from django.contrib.auth.models import User as UserType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models
from ulid2 import generate_ulid_as_uuid

from thunderstore.community.models import PackageListing
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.utils import capture_exception


class Comment(TimestampMixin, models.Model):
    thread = GenericForeignKey("thread_content_type", "thread_object_id")
    thread_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    # `thread_object_id` is a CharField to optimise the clean up comments task
    # As UUIDs cannot be casted to integers or vice versa, you are not able to compare
    # `thread_object_id` and `thread_content_type`'s `pk`.
    thread_object_id = models.CharField(max_length=36)
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
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

    def ensure_can_edit_content(self, user: UserType) -> None:
        # Only the comment author can edit a comment's content
        if user != self.author:
            raise PermissionDenied("Only the comment author can edit a message")

    def ensure_can_pin(self, user: UserType) -> None:
        commented_object = self.thread
        if isinstance(commented_object, PackageListing):
            # Must be a member of the identity to pin
            if not commented_object.package.owner.members.filter(
                user=user,
            ).exists():
                raise PermissionDenied("Must be a member to pin messages")
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
