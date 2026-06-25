import time

from django.core.management.base import BaseCommand

from thunderstore.core.session_cleanup import cleanup_expired_sessions


class Command(BaseCommand):
    help = "Delete expired Django sessions in batches"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10000,
            help="Number of rows to delete per batch (default: 10000)",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.1,
            help="Seconds to sleep between batches (default: 0.1)",
        )

    def handle(self, *args, **kwargs):
        batch_size = kwargs["batch_size"]
        sleep_time = kwargs["sleep"]

        self.stdout.write(
            f"Starting session cleanup "
            f"(batch_size={batch_size}, sleep={sleep_time}s)"
        )

        start = time.monotonic()

        total_deleted = cleanup_expired_sessions(
            batch_size=batch_size,
            sleep_time=sleep_time,
        )

        elapsed = time.monotonic() - start
        self.stdout.write(f"Deleted {total_deleted} expired sessions in {elapsed:.1f}s")
