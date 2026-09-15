from rest_framework.permissions import BasePermission


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
