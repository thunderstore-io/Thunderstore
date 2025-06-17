import itertools
from typing import Optional

import pytest

from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType
from thunderstore.webhooks.audit import AuditAction, AuditTarget
from thunderstore.webhooks.models import AuditWebhook
from thunderstore.webhooks.tasks import process_audit_event


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("target", "action"),
    list(
        itertools.product(
            [AuditTarget.PACKAGE, AuditTarget.LISTING, AuditTarget.VERSION],
            [AuditAction.APPROVED, AuditAction.REJECTED, AuditAction.WARNING],
        )
    ),
)
@pytest.mark.parametrize("message", (None, "Test message"))
def test_process_audit_event(
    active_package_listing: PackageListing,
    user: UserType,
    target: AuditTarget,
    action: AuditAction,
    message: Optional[str],
    mocker,
):
    mocked_post = mocker.patch("thunderstore.webhooks.tasks.audit.celery_post")

    webhook = AuditWebhook.objects.create(
        name="Webhook Test",
        webhook_url="http://127.0.0.1:8000/",
        is_active=True,
    )
    webhook.match_communities.set([active_package_listing.community])
    event = active_package_listing.build_audit_event(
        action=action,
        user_id=user.pk,
        message=message,
    )
    process_audit_event(event.json())
    assert mocked_post.called_once()
