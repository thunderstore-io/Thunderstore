from typing import Optional

from social_django.models import UserSocialAuth  # type: ignore

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package


def get_connection_avatar_url(connection: UserSocialAuth) -> Optional[str]:
    """
    Return URL associated with a given OAuth provider.
    """
    if connection.provider == "discord":
        user_id = connection.extra_data.get("id")
        avatar_id = connection.extra_data.get("avatar")

        if user_id and avatar_id:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png"

    elif connection.provider == "github" and connection.extra_data.get(
        "avatar_url",
    ):
        return connection.extra_data.get("avatar_url")

    elif connection.provider == "overwolf" and connection.extra_data.get(
        "avatar",
    ):
        return connection.extra_data.get("avatar")

    return None


def get_user_avatar_url(user: UserType) -> Optional[str]:
    """
    Return URL of one of the avatars user might have via OAuth providers.

    TODO: TS-1883.
    """
    for connection in user.social_auth.all():
        avatar_url = get_connection_avatar_url(connection)

        if avatar_url:
            return avatar_url

    return None
