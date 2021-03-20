from django.db import models
from ulid2 import generate_ulid_as_uuid


class Thread(models.Model):
    uuid = models.UUIDField(
        default=generate_ulid_as_uuid,
        editable=False,
        unique=True,
        primary_key=True,
    )

    @property
    def parent(self):
        # TODO: Use SupportedParentTypes
        for supported_parent_type_name, supported_parent_type_app_name in (
            ("packagelisting", "community"),
            ("comment", "repository"),
        ):
            parent = getattr(
                self,
                f"parent_{supported_parent_type_app_name}_{supported_parent_type_name}",
                None,
            )
            if parent:
                return parent
        raise Exception("Parent not found")


class CommentsThreadMixin(models.Model):
    """Mixin used to add comments to a model."""

    comments_thread = models.OneToOneField(
        Thread,
        on_delete=models.SET_NULL,
        related_name="parent_%(app_label)s_%(class)s",
        null=True,
    )

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.comments_thread:
            self.comments_thread.delete()
