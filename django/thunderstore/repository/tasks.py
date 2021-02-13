from celery import shared_task
from django.contrib.auth import get_user_model

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


@shared_task
def clean_up_comments() -> None:
    """Deletes comments with a deleted parent."""
    for comment in Comment.objects.iterator():
        if comment.thread is None:
            comment.delete()
