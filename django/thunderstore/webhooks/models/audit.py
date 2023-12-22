from django.db import models

from thunderstore.core.mixins import TimestampMixin


class AuditWebhook(TimestampMixin):
    name = models.TextField()
    webhook_url = models.CharField(max_length=2083)
    is_active = models.BooleanField(default=True)

    match_communities = models.ManyToManyField(
        "community.Community",
        related_name="audit_webhooks",
        help_text=(
            "Only match events from these communities. If empty, match all "
            "communities."
        ),
        blank=True,
    )

    def __str__(self):
        return self.name
