from typing import TYPE_CHECKING

from django.contrib.auth.models import User

if TYPE_CHECKING:
    from django.db.models import Manager

    from thunderstore.repository.models import Team

    class UserType(User):
        teams: "Manager[Team]"


else:
    UserType = None

__all__ = ["UserType"]
