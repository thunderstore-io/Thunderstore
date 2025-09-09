import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError

from thunderstore.account.models import ServiceAccount
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.permissions.utils import (
    PermissionResult,
    check_user_permissions,
    validate_user,
)


@pytest.mark.parametrize("fake_user", (None, AnonymousUser()))
def test_permissions_validate_user_not_signed_in(fake_user):
    with pytest.raises(ValidationError, match="Must be authenticated"):
        validate_user(fake_user)


@pytest.mark.django_db
def test_permissions_validate_user_inactive(user):
    user.is_active = False
    user.save()
    with pytest.raises(ValidationError, match="User has been deactivated"):
        validate_user(user)


@pytest.mark.django_db
def test_permissions_validate_user_serviceaccount_allowed(
    service_account: ServiceAccount,
):
    validate_user(service_account.user, allow_serviceaccount=True)


@pytest.mark.django_db
def test_permissions_validate_user_serviceaccount_disallowed(
    service_account: ServiceAccount,
):
    with pytest.raises(
        ValidationError, match="Service accounts are unable to perform this action"
    ):
        validate_user(service_account.user)


@pytest.mark.parametrize("fake_user", (None, AnonymousUser()))
def test_check_user_permissions_not_signed_in(fake_user):
    result = check_user_permissions(fake_user)
    assert not result.is_valid
    assert result.error == "Must be authenticated"
    assert result.is_public is True


@pytest.mark.django_db
def test_check_user_permissions_inactive(user):
    user.is_active = False
    user.save()

    result = check_user_permissions(user)
    assert not result.is_valid
    assert result.error == "User has been deactivated"
    assert result.is_public is False


@pytest.mark.django_db
def test_check_user_permissions_serviceaccount_allowed(service_account):
    result = check_user_permissions(service_account.user, allow_serviceaccount=True)
    assert result.is_valid
    assert result.error is None
    assert result.is_public is True


@pytest.mark.django_db
def test_check_user_permissions_serviceaccount_disallowed(service_account):
    result = check_user_permissions(service_account.user, allow_serviceaccount=False)
    assert not result.is_valid
    assert result.error == "Service accounts are unable to perform this action"
    assert result.is_public is True


def test_permission_result_valid_by_default():
    result = PermissionResult()
    assert result.is_valid
    assert result.error is None
    assert result.is_public is True


def test_permission_result_invalid_sets_error():
    result = PermissionResult(error="Something went wrong")
    assert not result.is_valid
    assert result.error == "Something went wrong"
    assert result.is_public is True


def test_permission_result_raise_if_invalid_valid_case_does_not_raise():
    result = PermissionResult()
    result.raise_if_invalid()  # Should not raise an error


@pytest.mark.parametrize("is_public", (True, False))
def test_permission_result_raise_if_invalid_invalid_case_raises(is_public):
    result = PermissionResult(error="Forbidden", is_public=is_public)
    with pytest.raises(PermissionValidationError, match="Forbidden") as exc_info:
        result.raise_if_invalid()
    assert exc_info.value.is_public is is_public


def test_permission_result_raise_if_invalid_with_custom_exception():
    result = PermissionResult(error="SomeOtherError")
    with pytest.raises(ValidationError, match="SomeOtherError"):
        result.raise_if_invalid(exc_cls=ValidationError)
