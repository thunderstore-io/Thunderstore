from datetime import datetime
from enum import Enum
from typing import List, Optional

from django.db import transaction
from pydantic import BaseModel


class AuditTarget(str, Enum):
    PACKAGE = "PACKAGE"
    LISTING = "LISTING"
    VERSION = "VERSION"


class AuditAction(str, Enum):
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    WARNING = "WARNING"


class AuditEventField(BaseModel):
    name: str
    value: str


class AuditEvent(BaseModel):
    timestamp: datetime
    user_id: Optional[int]
    community_id: Optional[int]
    target: AuditTarget
    action: AuditAction
    message: Optional[str]
    related_url: Optional[str]
    fields: Optional[List[AuditEventField]]


def fire_audit_event(event: AuditEvent):
    from .tasks import process_audit_event

    event_json = event.json()
    transaction.on_commit(lambda: process_audit_event.delay(event_json))
