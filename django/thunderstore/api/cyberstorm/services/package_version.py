from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from thunderstore.core.types import UserType
from thunderstore.repository.consts import MARKDOWN_FIELDS, MarkdownDocument
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)


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

    if (
        document == MarkdownDocument.CHANGELOG
        and version.pk != version.package.latest_id
    ):
        raise ValidationError("Changelogs can only be edited on the latest version")

    fields = MARKDOWN_FIELDS[document]
    now = timezone.now()
    is_override = content is not None
    changed = (
        PackageVersion.objects.filter(pk=version.pk)
        .exclude(**{fields.override: content})
        .update(
            **{
                fields.override: content,
                fields.edited_at: now if is_override else None,
                fields.edited_by: agent if is_override else None,
            }
        )
    )
    if changed:
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
