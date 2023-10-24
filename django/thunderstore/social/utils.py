from typing import Optional

from thunderstore.core.types import UserType


def get_avatar_url(user: UserType) -> Optional[str]:
    """
    TODO: TS-1883.
    """
    for connection in user.social_auth.all():
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
