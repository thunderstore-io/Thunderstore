from functools import wraps
from typing import Callable

from django.db import transaction


def run_after_commit(fn: Callable[..., None]) -> Callable[..., None]:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        transaction.on_commit(lambda: fn(*args, **kwargs))

    return wrapper
