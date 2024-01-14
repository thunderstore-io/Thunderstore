from typing import Literal, cast

from django.conf import settings
from django.core.cache import caches
from django_redis.cache import RedisCache

CacheName = Literal[
    "default",
    "legacy",
    "profiles",
]


def get_cache(name: CacheName) -> RedisCache:
    cache_name = name if settings.USE_MULTIPLE_CACHES else "default"

    class CacheProxy:
        """
        Proxy access to a cache implementation. Proxying is required as otherwise
        test fixtures are unable to modify the cache connection parameters
        dynamically during runtime.

        Implementation mostly copied from Django's built-in `DefaultCacheProxy`
        class, except here we can configure the cache alias that is proxied to.
        """

        def __getattr__(self, name):
            return getattr(caches[cache_name], name)

        def __setattr__(self, name, value):
            return setattr(caches[cache_name], name, value)

        def __delattr__(self, name):
            return delattr(caches[cache_name], name)

        def __contains__(self, key):
            return key in caches[cache_name]

        def __eq__(self, other):
            return caches[cache_name] == other

    return cast(RedisCache, CacheProxy())
