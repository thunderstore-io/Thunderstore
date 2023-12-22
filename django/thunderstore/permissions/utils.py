from typing import Optional

from django.core.exceptions import ValidationError

from thunderstore.core.types import UserType


def validate_user(
    user: Optional[UserType], allow_serviceaccount: bool = False
) -> UserType:
    if not user or not user.is_authenticated:
        raise ValidationError("Must be authenticated")
    if not user.is_active:
        raise ValidationError("User has been deactivated")
    if hasattr(user, "service_account") and not allow_serviceaccount:
        raise ValidationError("Service accounts are unable to perform this action")
    return user
