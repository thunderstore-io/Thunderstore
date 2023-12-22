import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

from thunderstore.account.models import ServiceAccount
from thunderstore.permissions.utils import validate_user


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
