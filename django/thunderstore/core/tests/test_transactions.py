from struct import pack
from typing import Any

import pytest
from django.db import DEFAULT_DB_ALIAS, connection, transaction

from thunderstore.core.transactions import (
    _get_lock_function_name,
    _get_lock_id_from_str,
    _get_xact_lock,
    atomic_lock,
)


@pytest.mark.parametrize(
    "wait, shared, expected",
    (
        (False, False, "pg_try_advisory_xact_lock"),
        (True, False, "pg_advisory_xact_lock"),
        (False, True, "pg_try_advisory_xact_lock_shared"),
        (True, True, "pg_advisory_xact_lock_shared"),
    ),
)
def test_transactions_get_lock_function_name(wait: bool, shared: bool, expected: str):
    assert _get_lock_function_name(wait, shared) == expected


@pytest.mark.parametrize(
    "lock_id_str",
    (
        "asiodfjwoigefjio jfojewijfo wjefiojweo f",
        "some-lock-name",
        "thunderstore.io",
        "hunter 2",
        "¤!(?(!¤()!?(?)(?!(#¤?)!#()?%#(?!)('_\x03",
    ),
)
def test_transactions_get_lock_id_from_str(lock_id_str: str) -> None:
    result = _get_lock_id_from_str(lock_id_str)
    assert pack("i", result)
    with pytest.raises(Exception):
        pack("i", 0xFFFFFFFF + 1)
    with pytest.raises(Exception):
        pack("i", -0xFFFFFFFF - 1)


@pytest.fixture
def db_id() -> int:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT oid FROM pg_database WHERE datname = %s",
        [connection.settings_dict["NAME"]],
    )
    db_id = cursor.fetchall()[0][0]
    cursor.close()
    return db_id


def _get_num_locks(db_id: int):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM pg_locks WHERE database = %s AND locktype = %s",
        [db_id, "advisory"],
    )
    lock_count = cursor.fetchall()[0][0]
    cursor.close()
    return lock_count


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("wait", (False, True))
@pytest.mark.parametrize("shared", (False, True))
def test_transactions_get_xact_lock(shared: bool, wait: bool, db_id: int):
    assert _get_num_locks(db_id) == 0
    with transaction.atomic():
        assert _get_num_locks(db_id) == 0
        result = _get_xact_lock(
            lock_id=1, using=DEFAULT_DB_ALIAS, wait=wait, shared=shared
        )
        assert result is True
        assert _get_num_locks(db_id) == 1
        result = _get_xact_lock(
            lock_id=5, using=DEFAULT_DB_ALIAS, wait=wait, shared=shared
        )
        assert result is True
        assert _get_num_locks(db_id) == 2
    assert _get_num_locks(db_id) == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("wait", (False, True))
@pytest.mark.parametrize("shared", (False, True))
def test_transactions_get_xact_lock_no_transaction(
    shared: bool, wait: bool, db_id: int
):
    assert _get_num_locks(db_id) == 0
    result = _get_xact_lock(lock_id=1, using=DEFAULT_DB_ALIAS, wait=wait, shared=shared)
    assert result is True  # The lock is acquired but immediately discarded
    assert _get_num_locks(db_id) == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("shared", (False, True))
def test_transactions_try_get_xact_lock_fails_if_taken_when_not_shared(
    db_id: int, shared: bool, settings: Any
):
    test_alias = f"{DEFAULT_DB_ALIAS}_test"
    settings.DATABASES[test_alias] = settings.DATABASES[DEFAULT_DB_ALIAS]
    with transaction.atomic():
        assert _get_num_locks(db_id) == 0
        assert (
            _get_xact_lock(lock_id=1, using=DEFAULT_DB_ALIAS, wait=False, shared=shared)
            is True
        )
        assert _get_num_locks(db_id) == 1
        assert (
            _get_xact_lock(lock_id=1, using=test_alias, wait=False, shared=shared)
            is shared
        )
    assert _get_num_locks(db_id) == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("wait", (False, True))
@pytest.mark.parametrize("shared", (False, True))
def test_transactions_atomic_lock(shared: bool, wait: bool, db_id: int):
    assert _get_num_locks(db_id) == 0
    with atomic_lock(lock_id="test-lock", wait=wait, shared=shared) as success:
        assert _get_num_locks(db_id) == 1
        assert success is True
    assert _get_num_locks(db_id) == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("shared", (False, True))
def test_transactions_atomic_lock_fails_if_taken_when_not_shared(
    db_id: int, shared: bool, settings: Any
):
    test_alias = f"{DEFAULT_DB_ALIAS}_test"
    settings.DATABASES[test_alias] = settings.DATABASES[DEFAULT_DB_ALIAS]
    assert _get_num_locks(db_id) == 0
    with atomic_lock(
        lock_id="test-lock", wait=False, shared=shared, using=DEFAULT_DB_ALIAS
    ) as success:
        assert success is True
        assert _get_num_locks(db_id) == 1
        with atomic_lock(
            lock_id="test-lock", wait=False, shared=shared, using=test_alias
        ) as success2:
            assert success2 is shared
            assert _get_num_locks(db_id) == (2 if shared else 1)
        assert _get_num_locks(db_id) == 1
    assert _get_num_locks(db_id) == 0


@pytest.mark.django_db(transaction=True)
def test_transactions_atomic_lock_fails_if_called_in_existing_transaction():
    with pytest.raises(ValueError) as e:
        with transaction.atomic():
            with atomic_lock("test-lock"):
                pass
    assert (
        "Unable to acquire a transaction scoped lock while already in a transaction"
        in str(e.value)
    )
