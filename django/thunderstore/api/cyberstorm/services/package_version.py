from typing import Dict, Optional

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)


@transaction.atomic
def update_markdown_overrides(
    agent: UserType,
    version: PackageVersion,
    overrides: Dict[str, Optional[str]],
) -> PackageVersion:
    # Allocate history IDs under the version lock so they follow write order.
    version = (
        PackageVersion.objects.select_for_update(of=("self",))
        .select_related("package", "package__owner")
        .get(pk=version.pk)
    )
    version.package.ensure_user_can_manage_wiki(agent)

    if "changelog" in overrides and version.pk != version.package.latest_id:
        raise ValidationError("Changelogs can only be edited on the latest version")

    now = timezone.now()
    updates = {}
    revisions = []
    for document in PackageVersionMarkdownRevision.Document.values:
        if document not in overrides:
            continue

        content = overrides[document]
        # Compare under the lock so retries do not duplicate history or
        # change attribution when the stored override has not changed.
        if content == getattr(version, f"{document}_override"):
            continue
        is_override = content is not None
        updates[f"{document}_override"] = content
        updates[f"{document}_override_edited_at"] = now if is_override else None
        updates[f"{document}_override_edited_by"] = agent if is_override else None
        revisions.append(
            PackageVersionMarkdownRevision(
                version=version,
                document=document,
                content=content if is_override else getattr(version, document),
                is_override=is_override,
                recorded_at=now,
                edited_at=now,
                edited_by=agent,
            )
        )

    if updates:
        PackageVersion.objects.filter(pk=version.pk).update(**updates)
        # Keep revision IDs in commit order across packages so polling cannot
        # skip an earlier ID from a transaction that finishes later.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext('markdown_revision_feed'))"
            )
        PackageVersionMarkdownRevision.objects.bulk_create(revisions)

    version.refresh_from_db()
    return version
