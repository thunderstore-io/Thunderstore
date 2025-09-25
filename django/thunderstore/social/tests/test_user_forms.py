import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import Http404

from thunderstore.social.views import DeleteAccountForm, LinkedAccountDisconnectForm

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_data, success", [("github", True), ("", False), (None, False)]
)
def test_linked_account_disconnect_form_validation(test_data, success):
    form = LinkedAccountDisconnectForm(data={"provider": test_data})
    if success:
        assert form.is_valid()
    else:

        assert not form.is_valid()
        assert "provider" in form.errors


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_data, success", [("github", True), ("", False), (None, False)]
)
def test_linked_account_disconnect_form_disconnect_account(
    user_with_social_auths, test_data, success
):
    form = LinkedAccountDisconnectForm(data={"provider": test_data})

    if success:
        assert form.is_valid()
        form.disconnect_account(test_data, user_with_social_auths)
        assert form.errors == {}
        assert not user_with_social_auths.social_auth.filter(
            provider=test_data
        ).exists()
    else:
        with pytest.raises(Http404, match="Social auth not found"):
            form.disconnect_account(test_data, user_with_social_auths)


@pytest.mark.django_db
def test_linked_account_disconnect_form_disconnect_last_auth_method(
    user_with_social_auths,
):
    user_with_social_auths.social_auth.filter(provider="discord").delete()
    form = LinkedAccountDisconnectForm(data={"provider": "github"})
    with pytest.raises(ValidationError):
        form.disconnect_account("github", user_with_social_auths)
    assert form.errors == {"__all__": ["Cannot disconnect last linked auth method"]}


@pytest.mark.django_db
def test_delete_account_form_validation(user):
    form = DeleteAccountForm(data={"verification": user.username}, user=user)
    assert form.is_valid()

    form = DeleteAccountForm(data={"verification": "wrong username"}, user=user)
    assert not form.is_valid()
    assert "verification" in form.errors


@pytest.mark.django_db
def test_delete_account_form_delete_user(user):
    form = DeleteAccountForm(data={"verification": user.username}, user=user)
    assert form.is_valid()
    form.delete_user()
    assert not User.objects.filter(username=user.username).exists()
