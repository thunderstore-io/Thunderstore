from django.conf import settings
from django.db import models
from django.utils import timezone


class PackageVersionMarkdownRevision(models.Model):
    """Saved overrides and resets, supplementing the immutable packaged markdown."""

    class Document(models.TextChoices):
        README = "readme", "README"
        CHANGELOG = "changelog", "CHANGELOG"

    version = models.ForeignKey(
        "repository.PackageVersion",
        related_name="markdown_revisions",
        on_delete=models.CASCADE,
    )
    document = models.CharField(max_length=9, choices=Document.choices)
    content = models.TextField(blank=True, null=True)
    is_override = models.BooleanField()
    recorded_at = models.DateTimeField(default=timezone.now, editable=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="markdown_revisions",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-id",)
        default_permissions = ("view",)
        indexes = [
            models.Index(
                fields=["version", "document", "-id"],
                name="markdown_revision_history_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(document__in=["readme", "changelog"]),
                name="markdown_revision_document",
            ),
            models.CheckConstraint(
                check=models.Q(content__isnull=False)
                | models.Q(document="changelog", is_override=False),
                name="markdown_revision_content",
            ),
        ]
