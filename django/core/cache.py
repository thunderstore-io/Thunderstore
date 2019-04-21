import time

from django.conf import settings
from django.core.cache import cache


# TODO: Improve to support parameters instead of just a static cache key
def cache_function_result(cache_key):
    def decorator(original_function):
        def wrapper(*args, **kwargs):
            def call_original():
                if settings.DEBUG and settings.DEBUG_SIMULATED_LAG:
                    time.sleep(settings.DEBUG_SIMULATED_LAG)
                return original_function(*args, **kwargs)
            return cache.get_or_set(key=cache_key, default=call_original)
        return wrapper
    return decorator
