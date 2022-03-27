from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.utils.decorators import run_after_commit


@run_after_commit
def invalidate_cache_on_commit_async(cache_bust_condition: str):
    if cache_bust_condition in settings.DISABLED_CACHE_BUST_CONDITIONS:
        return
    invalidate_cache.delay(cache_bust_condition)


@shared_task
def invalidate_cache(cache_bust_condition: str):
    if cache_bust_condition == CacheBustCondition.background_update_only:
        raise AttributeError("Invalid cache bust condition")
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"cache.{cache_bust_condition}.*")
