from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Clears all configured caches"

    def handle(self, *args, **kwargs):
        if settings.CACHES:
            cache.clear()
            self.stdout.write("Caches cleared!")
        else:
            raise CommandError("No caches are currently configured")
