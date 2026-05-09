from datetime import timedelta

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone

from thunderstore.core.session_cleanup import cleanup_expired_sessions


def _create_session(expire_date):
    store = SessionStore()
    store.create()
    Session.objects.filter(session_key=store.session_key).update(
        expire_date=expire_date,
    )
    return Session.objects.get(session_key=store.session_key)


@pytest.mark.django_db
def test_cleanup_deletes_only_expired_sessions():
    now = timezone.now()
    expired = [_create_session(now - timedelta(days=i)) for i in range(1, 4)]
    valid = [_create_session(now + timedelta(days=i)) for i in range(1, 3)]

    deleted = cleanup_expired_sessions(batch_size=10, sleep_time=0)

    assert deleted == 3
    remaining_keys = set(Session.objects.values_list("session_key", flat=True))
    for s in valid:
        assert s.session_key in remaining_keys
    for s in expired:
        assert s.session_key not in remaining_keys


@pytest.mark.django_db
def test_cleanup_returns_zero_when_no_expired():
    now = timezone.now()
    _create_session(now + timedelta(days=1))

    deleted = cleanup_expired_sessions(batch_size=10, sleep_time=0)

    assert deleted == 0
    assert Session.objects.count() == 1


@pytest.mark.django_db
def test_cleanup_processes_in_batches():
    now = timezone.now()
    for _ in range(10):
        _create_session(now - timedelta(days=1))

    deleted = cleanup_expired_sessions(batch_size=2, sleep_time=0)

    assert deleted == 10
    assert Session.objects.count() == 0


@pytest.mark.django_db
def test_cleanup_sleeps_between_batches(mocker):
    mock_sleep = mocker.patch("thunderstore.core.session_cleanup.time.sleep")
    now = timezone.now()
    for _ in range(5):
        _create_session(now - timedelta(days=1))

    deleted = cleanup_expired_sessions(batch_size=2, sleep_time=0.5)

    assert deleted == 5
    # 3 batches (2+2+1), sleep called 3 times
    assert mock_sleep.call_count == 3
    mock_sleep.assert_called_with(0.5)


@pytest.mark.django_db
def test_cleanup_logs_summary(mocker):
    mock_logger = mocker.patch("thunderstore.core.session_cleanup.logger")
    now = timezone.now()
    for _ in range(5):
        _create_session(now - timedelta(days=1))

    cleanup_expired_sessions(batch_size=2, sleep_time=0)

    mock_logger.info.assert_called_with(
        "Session cleanup complete: deleted 5 sessions in 3 batches"
    )


@pytest.mark.django_db
def test_cleanup_with_empty_table():
    deleted = cleanup_expired_sessions(batch_size=10, sleep_time=0)

    assert deleted == 0
    assert Session.objects.count() == 0
