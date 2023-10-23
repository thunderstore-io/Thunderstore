import pytest
from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.core.types import UserType
from thunderstore.social.utils import get_avatar_url


@pytest.mark.django_db
def test_get_avatar_url__for_user_without_connetions__returns_none(
    user: UserType,
) -> None:
    avatar = get_avatar_url(user)

    assert avatar is None


@pytest.mark.django_db
def test_get_avatar_url__for_discord_user__returns_none(user: UserType) -> None:
    UserSocialAuth.objects.create(
        user=user,
        provider="discord",
        uid="user",
        extra_data={"avatar": "url", "avatar_url": "url"},
    )

    avatar = get_avatar_url(user)

    # Discord doesn't return avatar URLs.
    assert avatar is None


@pytest.mark.django_db
def test_get_avatar_url__for_github_user__returns_avatar(user: UserType) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="github",
        uid="user",
    )

    avatar = get_avatar_url(user)

    assert avatar is None

    connection.extra_data = {"avatar_url": "url"}
    connection.save()

    avatar = get_avatar_url(user)

    assert avatar == "url"


@pytest.mark.django_db
def test_get_avatar_url__for_overwolf_user__returns_avatar(user: UserType) -> None:
    connection = UserSocialAuth.objects.create(
        user=user,
        provider="overwolf",
        uid="user",
    )

    avatar = get_avatar_url(user)

    assert avatar is None

    connection.extra_data = {"avatar": "url"}
    connection.save()

    avatar = get_avatar_url(user)

    assert avatar == "url"
