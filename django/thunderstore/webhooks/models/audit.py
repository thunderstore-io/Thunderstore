from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, QuerySet

from thunderstore.core.mixins import TimestampMixin
from thunderstore.webhooks.audit import AuditAction, AuditEvent
from thunderstore.webhooks.discord import (
    DiscordEmbed,
    DiscordEmbedField,
    DiscordPayload,
)

User = get_user_model()


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

    @classmethod
    def get_for_event(cls, event: AuditEvent) -> QuerySet["AuditWebhook"]:
        return cls.objects.filter(
            Q(is_active=True)
            & Q(Q(match_communities=None) | Q(match_communities=event.community_id))
        )

    @staticmethod
    def get_event_color(action: AuditAction) -> int:
        if (
            action == AuditAction.LISTING_APPROVED
            or action == AuditAction.VERSION_APPROVED
        ):
            return 5763719
        if (
            action == AuditAction.LISTING_REJECTED
            or action == AuditAction.VERSION_REJECTED
        ):
            return 15548997
        if (
            action == AuditAction.PACKAGE_WARNING
            or action == AuditAction.LISTING_WARNING
            or action == AuditAction.VERSION_WARNING
        ):
            return 16705372
        return 9807270

    @staticmethod
    def render_event(event: AuditEvent) -> DiscordPayload:
        agent_username = "System"

        if event.user_id:
            agent = User.objects.prefetch_related("social_auth").get(pk=event.user_id)
            agent_username = agent.username
            for entry in agent.social_auth.all():
                if entry.provider == "discord":
                    agent_username = f"<@{entry.uid}>"
                    break

        return DiscordPayload(
            embeds=[
                DiscordEmbed(
                    title=event.action,
                    description=event.message,
                    url=event.related_url,
                    color=AuditWebhook.get_event_color(event.action),
                    timestamp=event.timestamp.isoformat(),
                    fields=[
                        DiscordEmbedField(
                            name="Triggered by",
                            value=agent_username,
                        )
                    ]
                    + event.fields,
                )
            ]
        )
