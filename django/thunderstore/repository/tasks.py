from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import CharField
from django.db.models.functions import Cast

from thunderstore.repository.api.v1.tasks import update_api_v1_caches
from thunderstore.repository.models import Comment

User = get_user_model()


@shared_task
def update_api_caches():
    update_api_v1_caches()


@shared_task
def clean_up_comments() -> None:
    """
    Deletes comments with a deleted parent.

    This is equivalent to:

    for comment in Comment.objects.iterator():
        if comment.thread is None:
            comment.delete()
    """
    for content_type_id in Comment.objects.values_list(
        "thread_content_type",
    ).distinct():
        content_type = ContentType.objects.get(pk=content_type_id[0])
        model = content_type.model_class()
        for comment in Comment.objects.exclude(
            thread_object_id__in=model.objects.annotate(
                pk_as_text=Cast("pk", CharField(max_length=36)),
            ).values("pk_as_text"),
        ):
            comment.delete()
