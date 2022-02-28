from django.core.management.base import BaseCommand

from thunderstore.ts_github.models.keys import KeyProvider
from thunderstore.ts_github.utils import update_keys


class Command(BaseCommand):
    help = "Updates repository specific caches"

    def add_arguments(self, parser):
        parser.add_argument(
            "provider",
            type=str,
            help="Name of the key provider you want to update keys for",
        )

    def handle(self, *args, **kwargs):
        key_provider = None
        try:
            key_provider = KeyProvider.objects.get(name=kwargs["provider"])
        except KeyProvider.DoesNotExist:
            print(f"Provider {kwargs['provider']} does not exist")
            return
        update_keys(key_provider)
        print(f"Keys for {key_provider.identifier} has been updated")
