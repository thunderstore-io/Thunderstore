from typing import Optional

from thunderstore.core.types import UserType


def get_avatar_url(user: UserType) -> Optional[str]:
    """
    TODO: TS-1883.
    """
    for connection in user.social_auth.all():
        if connection.provider == "github" and connection.extra_data.get(
            "avatar_url",
        ):
            return connection.extra_data.get("avatar_url")

        if connection.provider == "overwolf" and connection.extra_data.get(
            "avatar",
        ):
            return connection.extra_data.get("avatar")

    return None
