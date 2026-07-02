import html
import re
from typing import List

import bleach
from django.core.exceptions import ValidationError
from django.db import models

from thunderstore.core.mixins import TimestampMixin


class CommunityNotificationType:
    """Severity of a community notification. Mirrors the legacy Django alert
    levels and maps onto the frontend alert variants."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    options = (CRITICAL, WARNING, INFO)


# Locates the "[label](" opening of the minimalistic [label](target) link
# syntax we support in otherwise plain-text notification content. The target
# itself is extracted with balanced-parenthesis matching (see
# iter_link_targets), mirroring how markdown parsers read link destinations, so
# that targets containing parentheses (e.g. "javascript:alert(1)") cannot slip
# past validation. Kept deliberately simple so it can be extended towards
# fuller markdown later.
LINK_OPEN_PATTERN = re.compile(r"\[[^\[\]]*\]\(")

# Only http(s) absolute links and root-relative internal links are permitted.
# Protocol-relative URLs (//host) are rejected as they resolve to absolute URLs.
ALLOWED_ABSOLUTE_SCHEMES = ("http://", "https://")


def iter_link_targets(text: str):
    """Yield the target of every [label](target) link in the text, matching
    link destinations with balanced parentheses like markdown does."""

    for match in LINK_OPEN_PATTERN.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth > 0:
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        if depth == 0:
            yield text[match.end() : index - 1]


def _validate_link_target(target: str) -> None:
    stripped = target.strip()
    if not stripped:
        raise ValidationError("Notification links must have a target.")
    if stripped.startswith("//"):
        raise ValidationError(f"Protocol-relative links are not allowed: {target!r}")
    if stripped.startswith("/"):
        return
    if stripped.lower().startswith(ALLOWED_ABSOLUTE_SCHEMES):
        return
    raise ValidationError(
        "Notification links must be root-relative (/...) or http(s) URLs: "
        f"{target!r}"
    )


def sanitize_notification_content(content: str) -> str:
    """Strip all HTML from the content, leaving plain text plus the supported
    [label](target) link syntax. Link targets are validated to be safe."""

    if not isinstance(content, str):
        raise ValidationError("Notification content must be a string.")

    # Remove any HTML tags entirely. bleach escapes stray entities (e.g. a
    # lone "&"), which we undo so the stored value stays true plain text; the
    # clients render it as text (not HTML), so this is safe.
    cleaned = html.unescape(
        bleach.clean(content, tags=[], attributes={}, protocols=[], strip=True)
    )

    if not cleaned.strip():
        raise ValidationError("Notification content must not be empty.")

    for target in iter_link_targets(cleaned):
        _validate_link_target(target)

    return cleaned


def validate_and_sanitize_notifications(value) -> List[dict]:
    if not isinstance(value, list):
        raise ValidationError("Notifications must be a list.")

    sanitized: List[dict] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValidationError(f"Notification #{index + 1} must be an object.")

        extra_keys = set(item.keys()) - {"type", "content"}
        if extra_keys:
            raise ValidationError(
                f"Notification #{index + 1} has unsupported fields: "
                f"{', '.join(sorted(extra_keys))}"
            )

        notification_type = item.get("type")
        if notification_type not in CommunityNotificationType.options:
            raise ValidationError(
                f"Notification #{index + 1} has an invalid type: "
                f"{notification_type!r}. Must be one of "
                f"{', '.join(CommunityNotificationType.options)}."
            )

        content = sanitize_notification_content(item.get("content"))
        sanitized.append({"type": notification_type, "content": content})

    return sanitized


class CommunityNotification(TimestampMixin, models.Model):
    """Community-scoped notifications shown to clients (e.g. at the top of the
    community package list). Stored as an ordered list so a community has 0..1
    rows; the first item is rendered first."""

    community = models.OneToOneField(
        "community.Community",
        on_delete=models.CASCADE,
        related_name="notification",
    )
    notifications = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Ordered list of {"type": "critical"|"warning"|"info", '
            '"content": "text"} objects. Content is plain text; links use the '
            "[label](target) syntax with http(s) or root-relative (/...) "
            "targets only."
        ),
    )

    def __str__(self):
        return f"Notifications for {self.community_id}"

    def clean(self):
        super().clean()
        self.notifications = validate_and_sanitize_notifications(self.notifications)

    def save(self, **kwargs):
        self.notifications = validate_and_sanitize_notifications(self.notifications)
        super().save(**kwargs)
