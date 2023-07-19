from typing import TYPE_CHECKING, Optional

from django.contrib.auth.models import User
from django.http import HttpRequest

if TYPE_CHECKING:
    from django.db.models import Manager

    from thunderstore.account.models import UserSettings
    from thunderstore.community.models import Community
    from thunderstore.repository.models import Team

    class UserType(User):
        teams: "Manager[Team]"
        settings: Optional[UserSettings]

    class HttpRequestType(HttpRequest):
        community: "Optional[Community]"

else:
    UserType = None
    HttpRequestType = None

__all__ = ["UserType", "HttpRequestType"]
