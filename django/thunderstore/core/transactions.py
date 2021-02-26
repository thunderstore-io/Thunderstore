from contextlib import contextmanager
from typing import Optional
from zlib import crc32

from django.db import DEFAULT_DB_ALIAS, connections, transaction


@contextmanager
def atomic_lock(
    lock_id: str,
    shared: bool = False,
    wait: bool = False,
    using: Optional[str] = None,
    savepoint: bool = True,
):
    if using is None:
        using = DEFAULT_DB_ALIAS

    if connections[using].in_atomic_block:
        raise ValueError(
            "Unable to acquire a transaction scoped lock while already in a transaction"
        )

    with transaction.atomic(using=using, savepoint=savepoint):
        yield _get_xact_lock(
            lock_id=_get_lock_id_from_str(lock_id),
            using=using,
            shared=shared,
            wait=wait,
        )


def _get_lock_id_from_str(lock_id_str: str) -> int:
    pos = crc32(lock_id_str.encode("utf-8"))
    result = (2 ** 31 - 1) & pos
    if pos & 2 ** 31:
        result -= 2 ** 31
    return result


def _get_lock_function_name(wait: bool, shared: bool) -> str:
    _try = "try_" if not wait else ""
    _shared = "_shared" if shared else ""
    return f"pg_{_try}advisory_xact_lock{_shared}"


def _get_xact_lock(lock_id: int, using: str, shared: bool, wait: bool) -> bool:
    function_name = _get_lock_function_name(wait=wait, shared=shared)
    command = f"SELECT {function_name}({lock_id})"

    cursor = connections[using].cursor()
    cursor.execute(command)

    if not wait:
        acquired = cursor.fetchone()[0]
    else:
        acquired = True

    return acquired
