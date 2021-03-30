import pytest
import rest_framework.exceptions

from thunderstore.account.authentication import UserSessionTokenAuthentication


@pytest.mark.django_db
def test_user_session_token(client, user):
    client.force_login(user)
    session_id = client.cookies["sessionid"].value
    authenticated_user, _ = UserSessionTokenAuthentication().authenticate_credentials(
        session_id,
    )
    assert authenticated_user == user


@pytest.mark.django_db
def test_user_session_token_invalid():
    with pytest.raises(
        rest_framework.exceptions.AuthenticationFailed,
        match="Invalid token.",
    ):
        UserSessionTokenAuthentication().authenticate_credentials("INVALID_SESSION_ID")


@pytest.mark.django_db
def test_user_session_token_inactive_user(client, user):
    user.is_active = False
    user.save()
    client.force_login(user)
    session_id = client.cookies["sessionid"].value
    with pytest.raises(
        rest_framework.exceptions.AuthenticationFailed,
        match="User inactive or deleted.",
    ):
        UserSessionTokenAuthentication().authenticate_credentials(session_id)
