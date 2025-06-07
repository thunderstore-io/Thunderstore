import pytest
from django.contrib.auth import get_user_model

from thunderstore.api.cyberstorm.services.user import (
    delete_user_account,
    delete_user_social_auth,
)
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType

User = get_user_model()


@pytest.mark.django_db
def test_delete_user_account_success(user: UserType):
    assert User.objects.filter(username=user.username).exists()
    delete_user_account(target_user=user)
    assert not User.objects.filter(username=user.username).exists()


@pytest.mark.django_db
def test_delete_user_social_auth_success(user_with_social_auths: UserType):
    social_auth = user_with_social_auths.social_auth.filter(provider="discord").first()
    delete_user_social_auth(social_auth=social_auth)
    assert not social_auth.pk


@pytest.mark.django_db
def test_delete_user_social_auth_last_auth_method_raises_error(
    user_with_social_auths: UserType,
):
    user_with_social_auths.social_auth.filter(provider="discord").delete()
    social_auth = user_with_social_auths.social_auth.first()
    with pytest.raises(PermissionValidationError):
        delete_user_social_auth(social_auth=social_auth)
