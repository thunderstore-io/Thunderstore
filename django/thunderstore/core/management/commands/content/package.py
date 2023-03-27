from typing import Collection, Optional

from django.db.models import signals

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.models import Package
from thunderstore.utils.iterators import print_progress


class PackagePopulator(ContentPopulator):
    packages: Optional[Collection[Package]] = None
    name_prefix = "Test_Package_"

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating packages...")
        packages = []

        # Disabling signals to avoid spamming cache clear calls
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(Package.post_save, sender=Package)
        signals.post_delete.disconnect(Package.post_delete, sender=Package)

        for team in print_progress(context.teams, len(context.teams)):
            existing = list(
                team.owned_packages.filter(name__startswith=self.name_prefix)[
                    : context.package_count
                ]
            )
            offset = len(existing)
            remainder = context.package_count - offset
            team_packages = [
                Package.objects.create(
                    owner=team,
                    name=f"{self.name_prefix}{i + offset}",
                    namespace=team.get_namespace(),
                )
                for i in range(remainder)
            ]
            packages += team_packages

        # Re-enabling previously disabled signals
        signals.post_save.connect(Package.post_save, sender=Package)
        signals.post_delete.connect(Package.post_delete, sender=Package)

        self.packages = packages

    def update_context(self, context) -> None:
        if self.packages:
            context.packages = self.packages
        else:
            context.packages = Package.objects.filter(
                owner__in=context.teams,
                name__startswith=self.name_prefix,
            )

    def clear(self) -> None:
        print("Deleting existing packages...")
        Package.objects.all().delete()
