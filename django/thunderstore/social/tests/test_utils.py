import pytest
from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.core.types import UserType
from thunderstore.social.utils import get_connection_avatar_url, get_user_avatar_url


@pytest.mark.django_db
def test_get_user_avatar_url__for_user_without_connetions__returns_none(
    user: UserType,
) -> None:
    user_avatar = get_user_avatar_url(user)

    assert user_avatar is None


@pytest.mark.django_db
def test_get_user_avatar_url__for_user_with_one_connetion__returns_avatar(
    user: UserType,
) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="github",
        uid="user",
        extra_data={"avatar_url": "url"},
    )

    user_avatar = get_user_avatar_url(user)
    connection_avatar = get_connection_avatar_url(connection)

    assert user_avatar is not None
    assert user_avatar != ""
    assert user_avatar == connection_avatar


@pytest.mark.django_db
def test_get_user_avatar_url__for_user_with_many_connetions__returns_avatar(
    user: UserType,
) -> None:
    UserSocialAuth.objects.create(
        user=user,
        provider="discord",
        uid="user",
        extra_data={"id": "user_id", "avatar": "avatar_id"},
    )
    UserSocialAuth.objects.create(
        user=user,
        provider="github",
        uid="user",
        extra_data={"avatar_url": "url"},
    )
    UserSocialAuth.objects.create(
        user=user,
        provider="overwolf",
        uid="user",
        extra_data={"avatar": "url"},
    )

    user_avatar = get_user_avatar_url(user)

    assert user_avatar is not None
    assert user_avatar != ""


@pytest.mark.django_db
def test_get_connection_avatar_url__for_unknown_provider__returns_none(
    user: UserType,
) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="thunderstore",
        uid="user",
        extra_data={"avatar": "url"},
    )

    connection_avatar = get_connection_avatar_url(connection)

    assert connection_avatar is None


@pytest.mark.django_db
def test_get_connection_avatar_url__for_discord__returns_avatar(user: UserType) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="discord",
        uid="user",
        extra_data={"id": "user_id", "avatar": "avatar_id"},
    )

    connection_avatar = get_connection_avatar_url(connection)

    assert type(connection_avatar) == str
    assert connection_avatar.endswith("avatars/user_id/avatar_id.png")


@pytest.mark.django_db
def test_get_connection_avatar_url__for_github_user__returns_avatar(
    user: UserType,
) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="github",
        uid="user",
        extra_data={"avatar_url": "url"},
    )

    connection_avatar = get_connection_avatar_url(connection)

    assert connection_avatar == "url"


@pytest.mark.django_db
def test_get_connection_avatar_url__for_overwolf_user__returns_avatar(
    user: UserType,
) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="overwolf",
        uid="user",
        extra_data={"avatar": "url"},
    )

    connection_avatar = get_connection_avatar_url(connection)

    assert connection_avatar == "url"
