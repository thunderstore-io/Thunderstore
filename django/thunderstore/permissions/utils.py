from typing import List, Optional

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType


def validate_user(
    user: Optional[UserType], allow_serviceaccount: bool = False
) -> UserType:
    if not user or not user.is_authenticated:
        raise PermissionValidationError("Must be authenticated")
    if not user.is_active:
        raise PermissionValidationError("User has been deactivated", is_public=False)
    if hasattr(user, "service_account") and not allow_serviceaccount:
        raise PermissionValidationError(
            "Service accounts are unable to perform this action"
        )
    return user


def check_user_permissions(
    user: Optional[UserType], allow_serviceaccount: bool = False
) -> List[str]:
    errors = []

    if not user or not user.is_authenticated:
        errors.append("Must be authenticated")
    elif not user.is_active:
        errors.append("User has been deactivated")
    elif hasattr(user, "service_account") and not allow_serviceaccount:
        errors.append("Service accounts are unable to perform this action")

    return errors
