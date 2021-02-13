from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from ulid2 import generate_ulid_as_uuid

from thunderstore.repository.api.experimental.tasks import (
    update_api_experimental_caches,
)
from thunderstore.repository.api.v1.tasks import update_api_v1_caches
from thunderstore.repository.models import Comment

User = get_user_model()


@shared_task
def update_api_caches():
    update_api_v1_caches()
    update_api_experimental_caches()


def _create_ghost_user_username(id_: str) -> str:
    return f"Ghost User {id_}"


def _create_ghost_user_email(id_: str) -> str:
    # The ID used in ghost user usernames and emails are not the same as their `User.id`
    # This is because `User` still uses an autoincrement ID
    return f"{id_}.gu@thunderstore.io"


@shared_task
def delete_user(user_id: int) -> None:
    """
    Delete a User.

    This should be the only place where User.delete() is called.
    """
    with transaction.atomic():
        user = User.objects.get(id=user_id)
        if not user.comments.exists():
            return
        uuid = generate_ulid_as_uuid()
        username = _create_ghost_user_username(uuid.hex)
        email = _create_ghost_user_email(uuid.hex)
        ghost_user = User.objects.create_user(username, email=email)
        for comment in user.comments.iterator():
            comment.author = ghost_user
            comment.save(update_fields=("author",))
        user.delete()


@shared_task
def clean_up_comments() -> None:
    """Deletes comments with a deleted parent."""
    for comment in Comment.objects.iterator():
        if comment.thread is None:
            comment.delete()
