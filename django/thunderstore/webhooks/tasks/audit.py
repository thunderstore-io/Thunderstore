from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.core.tasks import celery_post
from thunderstore.webhooks.audit import AuditEvent
from thunderstore.webhooks.models import AuditWebhook


@shared_task(
    name="thunderstore.webhooks.tasks.process_audit_event", queue=CeleryQueues.Default
)
def process_audit_event(event_json: str):
    event = AuditEvent.parse_raw(event_json)
    rendered = AuditWebhook.render_event(event).json(
        exclude_unset=True,
        exclude_none=True,
    )
    webhooks = AuditWebhook.get_for_event(event)
    for webhook in webhooks:
        celery_post.delay(
            webhook.webhook_url,
            data=rendered,
            headers={"Content-Type": "application/json"},
        )
