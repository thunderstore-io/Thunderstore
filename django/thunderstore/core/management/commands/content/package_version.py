from django.db.models import signals

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion
from thunderstore.utils.iterators import print_progress


class PackageVersionPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package versions...")

        # Disabling signals to avoid spamming cache clear calls and other
        # needless action
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.disconnect(
            PackageVersion.post_delete, sender=PackageVersion
        )
        signals.post_save.disconnect(Package.post_save, sender=Package)
        signals.post_delete.disconnect(Package.post_delete, sender=Package)

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            vercount = package.versions.count()
            for vernum in range(context.version_count - vercount):
                PackageVersionFactory.create(
                    package=package,
                    name=package.name,
                    version_number=f"{vernum + vercount}.0.0",
                    website_url="https://example.org",
                    description=f"Example mod {i}",
                    readme=f"# This is an example mod number {i}",
                    changelog=f"# Example changelog for mod number {i}",
                )

            # Manually calling would-be signals once per package, as it doesn't
            # actually make use of the sender param at all (and can be None)
            package.handle_created_version(None)
            package.handle_updated_version(None)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
        signals.post_save.connect(Package.post_save, sender=Package)
        signals.post_delete.connect(Package.post_delete, sender=Package)

    def clear(self) -> None:
        print("Deleting existing package versions...")
        PackageVersion.objects.all().delete()
