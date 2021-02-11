from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied

from thunderstore.account.models import ServiceAccount
from thunderstore.repository.models import Package


def ensure_can_rate_package(user: User, package: Package):
    if not user or not user.is_authenticated:
        raise PermissionDenied("Must be logged in")
    if ServiceAccount.objects.filter(user=user).exists():
        raise PermissionDenied("Service accounts are unable to rate packages")
    return True
