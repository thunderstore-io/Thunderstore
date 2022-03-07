from django.core.management.base import BaseCommand

from thunderstore.ts_github.models.keys import KeyProvider
from thunderstore.ts_github.utils import update_keys


class Command(BaseCommand):
    help = "Updates key provider specific keys e.g. github"

    def add_arguments(self, parser):
        parser.add_argument(
            "providers",
            nargs="?",
            type=str,
            default=False,
            help="Identifiers of the key providers you want to update keys for",
        )

    def handle(self, *args, **kwargs):
        if kwargs["providers"]:
            for provider_str in kwargs["providers"]:
                provider = None
                try:
                    provider = KeyProvider.objects.get(name=provider_str)
                except KeyProvider.DoesNotExist:
                    print(f"Provider {provider_str} does not exist")
                    return
            update_keys(provider)
            print(f"Keys for {provider.identifier} has been updated")
        else:
            all_providers = KeyProvider.objects.all()
            for provider in all_providers:
                update_keys(provider)
                print(f"Keys for {provider.identifier} has been updated")
