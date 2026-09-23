from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.models import PackageVersion


def can_view_markdown_revisions(user) -> bool:
    return user.has_perm("repository.view_packageversionmarkdownrevision")


def ensure_user_can_view_markdown_history(
    agent: UserType, version: PackageVersion
) -> None:
    agent = validate_user(agent)
    if agent.is_staff or can_view_markdown_revisions(agent):
        return

    for listing in version.package.community_listings.select_related("community"):
        if listing.community.can_user_manage_packages(agent):
            return

    raise PermissionValidationError(
        "Must be a moderator of a listed community or an administrator to view markdown history"
    )
