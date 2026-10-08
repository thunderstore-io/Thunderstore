from typing import Optional

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from thunderstore.core.types import UserType
from thunderstore.repository.consts import MARKDOWN_FIELDS, MarkdownDocument
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)

# Arbitrary, only needs to be unique among our advisory locks.
MARKDOWN_REVISION_FEED_LOCK_ID = 1239


def update_markdown_override(
    agent: UserType,
    version: PackageVersion,
    document: MarkdownDocument,
    content: str,
) -> PackageVersion:
    return _write_markdown_override(agent, version, document, content)


def delete_markdown_override(
    agent: UserType,
    version: PackageVersion,
    document: MarkdownDocument,
) -> PackageVersion:
    return _write_markdown_override(agent, version, document, None)


@transaction.atomic
def _write_markdown_override(
    agent: UserType,
    version: PackageVersion,
    document: MarkdownDocument,
    content: Optional[str],
) -> PackageVersion:
    version.package.ensure_user_can_manage_wiki(agent)

    # Concurrent saves to the same version are applied in lock order.
    version = (
        PackageVersion.objects.select_for_update(of=("self",))
        .select_related("package")
        .get(pk=version.pk)
    )

    if (
        document == MarkdownDocument.CHANGELOG
        and version.pk != version.package.latest_id
    ):
        raise ValidationError("Changelogs can only be edited on the latest version")

    fields = MARKDOWN_FIELDS[document]
    # Saving the same content again (e.g. a retry) shouldn't add history
    # or change who last edited it.
    if content == getattr(version, fields.override):
        return version

    now = timezone.now()
    is_override = content is not None
    PackageVersion.objects.filter(pk=version.pk).update(
        **{
            fields.override: content,
            fields.edited_at: now if is_override else None,
            fields.edited_by: agent if is_override else None,
        }
    )
    # Revision IDs must commit in order, otherwise the feed can skip an ID
    # whose transaction commits after a higher one.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)", [MARKDOWN_REVISION_FEED_LOCK_ID]
        )
    PackageVersionMarkdownRevision.objects.create(
        version=version,
        document=document,
        content=content if is_override else getattr(version, fields.original),
        is_override=is_override,
        recorded_at=now,
        edited_at=now,
        edited_by=agent,
    )

    version.refresh_from_db()
    return version
