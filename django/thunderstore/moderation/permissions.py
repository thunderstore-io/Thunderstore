from rest_framework.permissions import BasePermission

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.models import PackageVersion


def is_security_moderator(user) -> bool:
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser or user.groups.filter(name="Security Moderator").exists()
        )
    )


class IsSecurityModerator(BasePermission):
    def has_permission(self, request, view):
        return is_security_moderator(request.user)


def ensure_user_can_view_markdown_history(
    agent: UserType, version: PackageVersion
) -> None:
    agent = validate_user(agent)
    if agent.is_staff or is_security_moderator(agent):
        return

    for listing in version.package.community_listings.select_related("community"):
        if listing.community.can_user_manage_packages(agent):
            return

    raise PermissionValidationError(
        "Must be a moderator of a listed community or an administrator to view markdown history"
    )
