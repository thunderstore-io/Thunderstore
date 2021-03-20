from rest_framework.exceptions import PermissionDenied

from thunderstore.account.models import ServiceAccount
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package


def ensure_can_rate_package(user: UserType, package: Package):
    if not user or not user.is_authenticated:
        raise PermissionDenied("Must be logged in")
    if user.is_active is False:
        raise PermissionDenied("User has been deactivated")
    if ServiceAccount.objects.filter(user=user).exists():
        raise PermissionDenied("Service accounts are unable to rate packages")
    return True
