from typing import Dict, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageVersion


@transaction.atomic
def update_markdown_overrides(
    agent: UserType,
    version: PackageVersion,
    overrides: Dict[str, Optional[str]],
) -> PackageVersion:
    version.package.owner.ensure_user_can_manage_packages(agent)

    if "changelog" in overrides and version.pk != version.package.latest_id:
        raise ValidationError("Changelogs can only be edited on the latest version")

    now = timezone.now()

    if "readme" in overrides:
        readme = overrides["readme"]
        PackageVersion.objects.filter(pk=version.pk).update(
            readme_override=readme,
            readme_override_edited_at=now if readme is not None else None,
            readme_override_edited_by=agent if readme is not None else None,
        )

    if "changelog" in overrides:
        changelog = overrides["changelog"]
        PackageVersion.objects.filter(pk=version.pk).update(
            changelog_override=changelog,
            changelog_override_edited_at=now if changelog is not None else None,
            changelog_override_edited_by=agent if changelog is not None else None,
        )

    version.refresh_from_db()
    return version
