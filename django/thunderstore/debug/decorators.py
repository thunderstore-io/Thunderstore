from functools import wraps
from typing import Callable

from django.conf import settings
from django.db import connection, reset_queries


def print_query_stats(fn: Callable[..., None]) -> Callable[..., None]:
    """
    Print information about the database queries executed by a function

    This is intended only for development use, where it can be used to
    e.g. check that ORM's select_related() and prefetch_related() fetch
    all required information at once.

    NOTE: Active caching will distort the results.
    NOTE: Doesn't work on nested functions.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not settings.DEBUG:
            return fn(*args, **kwargs)

        reset_queries()
        result = fn(*args, **kwargs)
        queries = len(connection.queries)
        duration = sum([float(query["time"]) for query in connection.queries])

        print("*" * 72)
        print(f"* Function {fn.__name__} executed {queries} queries in {duration}s")
        print("*" * 72)

        return result

    return wrapper
