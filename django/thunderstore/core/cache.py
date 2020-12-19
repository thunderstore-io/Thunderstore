import hashlib
import time
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from thunderstore.cache.models import DatabaseCache
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


def get_view_cache_name(cls):
    module = cls.__module__
    if module is None or module == str.__class__.__module__:
        return cls.__name__
    else:
        return module + "." + cls.__name__


class ManualCacheMixin(object):
    cache_until = None
    cache_expiry = DEFAULT_CACHE_EXPIRY

    def dispatch(self, *args, **kwargs):
        def get_default(*a, **kw):
            return super().dispatch(*a, **kw).render()

        if self.request.method != "GET":
            return get_default(*args, **kwargs)

        return cache_get_or_set(
            key=get_cache_key(
                cache_bust_condition=self.cache_until,
                cache_type="view",
                key=get_view_cache_name(type(self)),
                vary_on=args + tuple(kwargs.values()) + (self.request.community_site,),
            ),
            default=get_default,
            default_args=args,
            default_kwargs=kwargs,
            expiry=self.cache_expiry,
        )


class BackgroundUpdatedCacheMixin(object):
    cache_database_fallback = True

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse("Cache missing")

    @classmethod
    def get_cache_key(cls, request, *args, **kwargs):
        return get_cache_key(
            cache_bust_condition=CacheBustCondition.background_update_only,
            cache_type="view",
            key=get_view_cache_name(cls),
            vary_on=args + tuple(kwargs.values()) + (request.community_site,),
        )

    @classmethod
    def get_cache(cls, key, default):
        result = cache.get(key, None)
        if result:
            return result
        elif cls.cache_database_fallback:
            db_result = DatabaseCache.get(key, None)
            if db_result:
                cache.set(key, db_result, None)
                return db_result
        return default

    @classmethod
    def set_cache(cls, key, value, timeout):
        result = cache.set(key, value, timeout)
        if cls.cache_database_fallback:
            DatabaseCache.set(key, value, timeout)
        return result

    def dispatch(self, *args, **kwargs):
        if self.request.method != "GET" or kwargs.get("skip_cache", False) is True:
            return super().dispatch(*args, **kwargs).render()
        return self.get_cache(
            self.get_cache_key(*args, **kwargs), self.get_no_cache_response()
        )

    @classmethod
    def update_cache(cls, view, *args, **kwargs):
        kwargs.update({"skip_cache": True})
        result = view(*args, **kwargs)
        del kwargs["skip_cache"]
        cls.set_cache(
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
