import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from sentry_sdk import capture_exception as capture_sentry_exception
from ulid2 import generate_ulid_as_uuid


class ChoiceEnum(object):
    @classmethod
    def as_choices(cls):
        return [
            (key, value)
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]

    @classmethod
    def options(cls):
        return [
            value
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]


def ensure_fields_editable_on_creation(readonly_fields, obj, editable_fields):
    if obj:
        return readonly_fields
    else:
        # Creating the object so make restaurant editable
        return list(x for x in readonly_fields if x not in editable_fields)


class CommunitySiteSerializerContext:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["community_site"] = self.request.community_site
        return context


def capture_exception(exception: Exception) -> None:
    """Raises exception when running tests or NO_SILENT_FAIL."""
    testing = "PYTEST_CURRENT_TEST" in os.environ
    if testing or not settings.SILENT_FAIL:
        raise exception
    if not testing and settings.SENTRY_DSN:
        capture_sentry_exception(exception)


def _create_ghost_user_username(id_: str) -> str:
    return f"Ghost User {id_}"


def _create_ghost_user_email(id_: str) -> str:
    # The ID used in ghost user usernames and emails are not the same as their `User.id`
    # This is because `User` still uses an autoincrement ID
    return f"{id_}.gu@thunderstore.io"


@transaction.atomic
def delete_user(user: User) -> None:
    """
    Delete a User.

    This should be the only place where User.delete() is called.
    """
    # Ghost user
    if user.comments.exists():
        uuid = generate_ulid_as_uuid()
        username = _create_ghost_user_username(uuid.hex)
        email = _create_ghost_user_email(uuid.hex)
        ghost_user = User.objects.create_user(username, email=email)
        for comment in user.comments.iterator():
            comment.author = ghost_user
            comment.save()

    user.delete()
