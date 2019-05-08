import time
import hashlib

from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache

from core.utils import ChoiceEnum


DEFAULT_CACHE_EXPIRY = 60 * 5


# TODO: Support parameters in cache bust conditions (e.g. specific package update)
class CacheBustCondition(ChoiceEnum):
    any_package_version_created = "any_package_version_created"
    any_package_version_updated = "any_package_version_updated"
    dynamic_html_updated = "dynamic_html_updated"


def cache_get_or_set(key, default, default_args=(), default_kwargs={}, expiry=None):
    def call_default():
        if settings.DEBUG and settings.DEBUG_SIMULATED_LAG:
            time.sleep(settings.DEBUG_SIMULATED_LAG)
        return default(*default_args, **default_kwargs)

    return cache.get_or_set(
        key=key,
        default=call_default,
        timeout=expiry,
    )


def invalidate_cache(cache_bust_condition):
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"cache.{cache_bust_condition}.*")


def get_cache_key(cache_bust_condition, cache_type, key, vary_on):
    if cache_bust_condition not in CacheBustCondition.options():
        raise ValueError(f"Invalid cache bust condition: {cache_bust_condition}")
    vary = "None"
    if vary_on:
        vary_args = ":".join(quote(str(var)) for var in vary_on)
        vary = hashlib.md5(vary_args.encode()).hexdigest()
    return f"cache.{cache_bust_condition}.{cache_type}.{key}.{vary}"


class ManualCacheMixin(object):
    cache_until = None
    cache_expiry = DEFAULT_CACHE_EXPIRY

    def dispatch(self, *args, **kwargs):

        def get_default(*a, **kw):
            return super(ManualCacheMixin, self).dispatch(*a, **kw).render()

        if self.request.method != "GET":
            return get_default(*args, **kwargs)

        return cache_get_or_set(
            key=get_cache_key(
                cache_bust_condition=self.cache_until,
                cache_type="view",
                key=type(self).__name__,
                vary_on=args + tuple(kwargs.values()),
            ),
            default=get_default,
            default_args=args,
            default_kwargs=kwargs,
            expiry=self.cache_expiry,
        )


def cache_function_result(cache_until, expiry=DEFAULT_CACHE_EXPIRY):
    def decorator(original_function):
        def wrapper(*args, **kwargs):
            return cache_get_or_set(
                key=get_cache_key(
                    cache_bust_condition=cache_until,
                    cache_type="func",
                    key=original_function.__name__,
                    vary_on=args + tuple(kwargs.values()),
                ),
                default=original_function,
                default_args=args,
                default_kwargs=kwargs,
                expiry=expiry,
            )
        return wrapper
    return decorator
