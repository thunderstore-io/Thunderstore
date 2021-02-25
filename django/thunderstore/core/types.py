from typing import TYPE_CHECKING

from django.contrib.auth.models import User

if TYPE_CHECKING:
    from django.db.models import Manager

    from thunderstore.repository.models import UploaderIdentity

    class UserType(User):
        uploader_identities: "Manager[UploaderIdentity]"


else:
    UserType = None

__all__ = ["UserType"]
