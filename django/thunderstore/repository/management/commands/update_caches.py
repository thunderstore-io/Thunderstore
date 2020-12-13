from django.core.management.base import BaseCommand

from thunderstore.repository.api.experimental.tasks import update_api_experimental_caches
from thunderstore.repository.api.v1.tasks import update_api_v1_caches


class Command(BaseCommand):
    help = "Updates repository specific caches"

    def handle(self, *args, **kwargs):
        print("Updating caches")
        update_api_v1_caches()
        update_api_experimental_caches()
        print("Caches updated!")
