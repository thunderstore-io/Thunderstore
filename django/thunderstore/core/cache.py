import time
import hashlib

from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from thunderstore.core.utils import ChoiceEnum


DEFAULT_CACHE_EXPIRY = 60 * 5


# TODO: Support parameters in cache bust conditions (e.g. specific package update)
class CacheBustCondition(ChoiceEnum):
    background_update_only = "manual_update_only"
    any_package_updated = "any_package_updated"
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
    if cache_bust_condition == CacheBustCondition.background_update_only:
        raise AttributeError("Invalid cache bust condition")
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


class BackgroundUpdatedCacheMixin(object):

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse("Cache missing")

    @classmethod
    def get_cache_key(cls, *args, **kwargs):
        return get_cache_key(
            cache_bust_condition=CacheBustCondition.background_update_only,
            cache_type="view",
            key=cls.__name__,
            vary_on=args + tuple(kwargs.values()),
        )

    def dispatch(self, *args, **kwargs):
        if self.request.method != "GET" or kwargs.get("skip_cache", False) is True:
            return super(BackgroundUpdatedCacheMixin, self).dispatch(*args, **kwargs).render()

        return cache.get(
            self.get_cache_key(*args, **kwargs),
            self.get_no_cache_response()
        )

    @classmethod
    def update_cache(cls, view, *args, **kwargs):
        kwargs.update({"skip_cache": True})
        result = view(*args, **kwargs)
        del kwargs["skip_cache"]
        cache.set(
            key=cls.get_cache_key(*args, **kwargs),
            value=result,
            timeout=None,
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
