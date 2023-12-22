from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from thunderstore.core.types import UserType
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.models import Package


def ensure_can_rate_package(user: UserType, package: Package):
    try:
        validate_user(user)
    except ValidationError as e:
        raise PermissionDenied(e.message) from e
    return True
