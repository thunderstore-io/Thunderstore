from django.db import models
from ulid2 import generate_ulid_as_uuid


class Thread(models.Model):
    uuid = models.UUIDField(
        default=generate_ulid_as_uuid,
        editable=False,
        unique=True,
        primary_key=True,
    )


class CommentsThreadMixin(models.Model):
    """Mixin used to add comments to a model."""

    comments_thread = models.OneToOneField(
        Thread,
        on_delete=models.SET_NULL,
        related_name="parent",
        null=True,
    )

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.comments_thread:
            self.comments_thread.delete()
