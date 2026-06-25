import logging
import time

from django.contrib.sessions.models import Session
from django.utils import timezone

logger = logging.getLogger(__name__)


def cleanup_expired_sessions(
    batch_size: int = 10000,
    sleep_time: float = 0.1,
) -> int:
    """
    Delete expired Django sessions in batches to avoid long-held locks.

    Args:
        batch_size: Number of rows to delete per batch.
        sleep_time: Seconds to sleep between batches.

    Returns:
        Total number of deleted rows.
    """
    total_deleted = 0
    batch_count = 0
    now = timezone.now()

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")
    if sleep_time < 0:
        raise ValueError("sleep_time must be greater than or equal to 0")

    while True:
        expired_session_keys = list(
            Session.objects.filter(expire_date__lt=now).values_list(
                "session_key", flat=True
            )[:batch_size]
        )

        if not expired_session_keys:
            break

        deleted, _ = Session.objects.filter(
            session_key__in=expired_session_keys
        ).delete()

        total_deleted += deleted
        batch_count += 1

        if deleted == 0:
            break

        if sleep_time > 0:
            time.sleep(sleep_time)

    logger.info(
        f"Session cleanup complete: deleted {total_deleted} sessions "
        f"in {batch_count} batches"
    )

    return total_deleted
