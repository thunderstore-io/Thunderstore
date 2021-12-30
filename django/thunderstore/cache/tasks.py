from celery import shared_task
from django.core.cache import cache
from django.db import transaction

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.core.utils import on_commit_or_immediate


def invalidate_cache_on_commit_async(cache_bust_condition: str):
    on_commit_or_immediate(lambda: invalidate_cache.delay(cache_bust_condition))


@shared_task
def invalidate_cache(cache_bust_condition: str):
    if cache_bust_condition == CacheBustCondition.background_update_only:
        raise AttributeError("Invalid cache bust condition")
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"cache.{cache_bust_condition}.*")
