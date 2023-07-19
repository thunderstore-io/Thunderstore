import pytest

from thunderstore.account.models import UserSettings
from thunderstore.core.types import UserType


@pytest.mark.django_db
def test_account_user_settings_get_for_user_creation(user: UserType):
    assert UserSettings.objects.count() == 0
    assert user.settings is None
    settings = UserSettings.get_for_user(user)
    assert settings is not None
    assert UserSettings.objects.count() == 1


@pytest.mark.django_db
def test_account_user_settings_get_for_user_retrieval(user_with_settings: UserType):
    assert UserSettings.objects.count() == 1
    assert user_with_settings.settings is not None
    settings = UserSettings.get_for_user(user_with_settings)
    assert settings == user_with_settings.settings
    assert UserSettings.objects.count() == 1
