from datetime import datetime
from enum import Enum
from typing import List, Optional

from django.db import transaction
from pydantic import BaseModel


class AuditAction(str, Enum):
    PACKAGE_WARNING = "PACKAGE_WARNING"
    LISTING_REJECTED = "LISTING_REJECTED"
    LISTING_APPROVED = "LISTING_APPROVED"
    LISTING_WARNING = "LISTING_WARNING"
    VERSION_REJECTED = "VERSION_REJECTED"
    VERSION_APPROVED = "VERSION_APPROVED"
    VERSION_WARNING = "VERSION_WARNING"


class AuditEventField(BaseModel):
    name: str
    value: str


class AuditEvent(BaseModel):
    timestamp: datetime
    user_id: Optional[int]
    community_id: Optional[int]
    action: AuditAction
    message: Optional[str]
    related_url: Optional[str]
    fields: Optional[List[AuditEventField]]


def fire_audit_event(event: AuditEvent):
    from .tasks import process_audit_event

    event_json = event.json()
    transaction.on_commit(lambda: process_audit_event.delay(event_json))
