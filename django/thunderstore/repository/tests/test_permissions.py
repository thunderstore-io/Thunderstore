import pytest
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from conftest import TestUserTypes
from thunderstore.repository.permissions import ensure_can_rate_package


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_permissions_ensure_can_rate_package(user_type, package):
    should_succeed = (TestUserTypes.regular_user, TestUserTypes.superuser)
    should_fail = (
        TestUserTypes.no_user,
        TestUserTypes.unauthenticated,
        TestUserTypes.deactivated_user,
        TestUserTypes.service_account,
    )

    if user_type not in set(should_succeed + should_fail):
        raise ValidationError(f"Unhandled user type: {user_type}")
    if user_type in should_succeed and user_type in should_fail:
        raise ValidationError("User type cannot be expected to succeed and fail")

    user = TestUserTypes.get_user_by_type(user_type)

    if user_type in should_succeed:
        assert ensure_can_rate_package(user, package) is True

    if user_type in should_fail:
        with pytest.raises(PermissionDenied):
            ensure_can_rate_package(user, package)
