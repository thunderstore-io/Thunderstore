from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clears all configured caches"

    def add_arguments(self, parser) -> None:
        parser.add_argument("caches", nargs="*", default=["default"])
        parser.add_argument("--all", default=False, action="store_true")

    def handle(self, *args, **kwargs):
        names = kwargs.get("caches", ["default"])
        if kwargs.get("all") is True:
            names = settings.CACHES.keys()

        for name in names:
            if name in settings.CACHES:
                self.stdout.write(f"Clearing cache: {name}")
                caches[name].clear()
            else:
                self.stderr.write(f"Cache {name} not found, unable to clear")

        self.stdout.write("All done!")
