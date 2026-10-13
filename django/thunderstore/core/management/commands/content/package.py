from typing import Collection, Optional

from django.db.models import signals

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
    package_identity,
    seeded_random,
)
from thunderstore.repository.models import Package
from thunderstore.utils.iterators import print_progress

# Probability that a generated package is flagged with the respective "tag" so
# the pinned/deprecated badges show up in the UI on a portion of the test data.
# Deprecation is applied by the version populator rather than here, because
# Package.handle_created_version() resets is_deprecated when versions are added.
PINNED_PROBABILITY = 0.15
DEPRECATED_PROBABILITY = 0.15


def desired_deprecated(package) -> bool:
    # "deprecated" left every default Test_Team_*/Test_Package_0 roll above
    # DEPRECATED_PROBABILITY, so a fresh create_test_data run had no badge.
    rng = seeded_random("status-deprecated", package_identity(package))
    return rng.random() < DEPRECATED_PROBABILITY


def desired_pinned(package) -> bool:
    rng = seeded_random("pinned", package_identity(package))
    return rng.random() < PINNED_PROBABILITY


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
            namespace = team.get_namespace()
            team_packages = []
            for i in range(remainder):
                package = Package(
                    owner=team,
                    name=f"{self.name_prefix}{i + offset}",
                    namespace=namespace,
                )
                package.is_pinned = desired_pinned(package)
                package.save()
                team_packages.append(package)
            for package in existing:
                is_pinned = desired_pinned(package)
                if package.is_pinned != is_pinned:
                    package.is_pinned = is_pinned
                    package.save(update_fields=("is_pinned",))
            packages += existing + team_packages

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
