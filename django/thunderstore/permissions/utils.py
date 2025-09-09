from dataclasses import dataclass
from typing import Optional

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType


@dataclass
class PermissionResult:
    error: Optional[str] = None
    is_public: bool = True

    @property
    def is_valid(self) -> bool:
        return self.error is None

    def raise_if_invalid(self, exc_cls=PermissionValidationError) -> None:
        if self.is_valid:
            return

        if exc_cls is PermissionValidationError:
            raise exc_cls(self.error, is_public=self.is_public)

        raise exc_cls(self.error)


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
) -> PermissionResult:

    result = PermissionResult()

    if not user or not user.is_authenticated:
        result.error = "Must be authenticated"
    elif not user.is_active:
        result.error = "User has been deactivated"
        result.is_public = False
    elif hasattr(user, "service_account") and not allow_serviceaccount:
        result.error = "Service accounts are unable to perform this action"

    return result
