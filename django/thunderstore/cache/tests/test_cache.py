import time
from typing import Any

from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition


def test_cache_clear_with_args() -> None:
    @cache_function_result(CacheBustCondition.background_update_only)
    def get_time(cache_vary: Any) -> float:
        return time.time()

    first = get_time("test")
    time.sleep(0.01)
    first_cached = get_time("test")
    second = get_time("test2")
    assert first == first_cached
    assert second > first
    time.sleep(0.01)
    get_time.clear_cache_with_args("test")
    first_busted = get_time("test")
    assert first_busted > first
    assert first_busted > second
