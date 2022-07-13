import hashlib
import time
import warnings
from typing import Any, Callable, Optional
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from redis.exceptions import LockError

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.repository.mixins import CommunityMixin

DEFAULT_CACHE_EXPIRY = 60 * 5
CACHE_LOCK_TIMEOUT = 30


def try_regenerate_cache(
    key: str,
    old_key: str,
    generator: Callable,
    timeout: int,
    old_timeout: int,
    version=None,
) -> Any:
    with cache.lock(
        f"lock.cachegenerate.{key}", timeout=CACHE_LOCK_TIMEOUT, blocking_timeout=None
    ):
        generated = generator()
        if generated is None:
            # TODO: Use some empty object instead which can be used to
            #       recognize None was cached
            warnings.warn(
                "Attempted to set 'None' to cache, replacing with empty string",
            )
            generated = ""
        cache.set(key, generated, timeout=timeout, version=version)
        cache.set(
            old_key,
            generated,
            timeout=old_timeout,
            version=version,
        )
        return generated


def regenerate_cache(
    key: str, generator: Callable, timeout: int, old_timeout: int, version=None
):
    old_key = f"old.{key}"
    try:
        return try_regenerate_cache(
            key=key,
            old_key=old_key,
            generator=generator,
            timeout=timeout,
            old_timeout=old_timeout,
            version=version,
        )
    except (LockError, AttributeError):
        # Lock was taken by another thread, check fallback version
        generated = cache.get(old_key, version=version)
        if generated is None:
            # Finally fall back to generating it on this thread
            generated = generator()
            cache.set(key, generated, timeout=timeout, version=version)
            cache.set(old_key, generated, timeout=None, version=version)
        return generated


def cache_get_or_set_by_key(
    condition: str,
    cache_key: str,
    cache_vary,
    get_default,
    default_args=(),
    default_kwargs=None,
    expiry=DEFAULT_CACHE_EXPIRY,
):
    if default_kwargs is None:
        default_kwargs = {}

    return cache_get_or_set(
        key=get_cache_key(
            cache_bust_condition=condition,
            cache_type="key",
            key=cache_key,
            vary_on=cache_vary,
        ),
        default=get_default,
        default_args=default_args,
        default_kwargs=default_kwargs,
        expiry=expiry,
    )


def cache_get_or_set(
    key, default, default_args=(), default_kwargs=None, expiry: Optional[int] = None
):
    if default_kwargs is None:
        default_kwargs = {}

    def call_default():
        if settings.DEBUG and settings.DEBUG_SIMULATED_LAG:
            time.sleep(settings.DEBUG_SIMULATED_LAG)
        return default(*default_args, **default_kwargs)

    old_timeout = None
    if expiry is not None:
        old_timeout = expiry * 2

    result = cache.get(key, version=None)
    if result is None:
        result = regenerate_cache(
            key=key, generator=call_default, timeout=expiry, old_timeout=old_timeout
        )

    return result


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

    def get_extra_cache_vary(self):
        return set()

    def dispatch(self, *args, **kwargs):
        def get_default(*a, **kw):
            return super(ManualCacheMixin, self).dispatch(*a, **kw).render()

        if self.request.method != "GET":
            return get_default(*args, **kwargs)

        return cache_get_or_set(
            key=get_cache_key(
                cache_bust_condition=self.cache_until,
                cache_type="view",
                key=get_view_cache_name(type(self)),
                vary_on=args + tuple(kwargs.values()) + self.get_extra_cache_vary(),
            ),
            default=get_default,
            default_args=args,
            default_kwargs=kwargs,
            expiry=self.cache_expiry,
        )


class ManualCacheCommunityMixin(CommunityMixin, ManualCacheMixin):
    def get_extra_cache_vary(self):
        return (self.community_identifier,)


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

        def clear_cache_with_args(*args, **kwargs):
            key = get_cache_key(
                cache_bust_condition=cache_until,
                cache_type="func",
                key=original_function.__name__,
                vary_on=args + tuple(kwargs.values()),
            )
            old_key = f"old.{key}"
            cache.delete(key)
            cache.delete(old_key)

        wrapper.clear_cache_with_args = clear_cache_with_args
        return wrapper

    return decorator
