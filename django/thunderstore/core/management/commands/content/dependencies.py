from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.utils.iterators import print_progress


class DependencyPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Linking dependencies...")
        PackageVersion.dependencies.through.objects.all().delete()

        # Ensure we have at least one dependency and one dependant
        package_count = len(context.packages)
        if package_count < 2:
            print("Not enough packages to create dependencies.")
            return

        dependency_count = min(context.dependency_count, package_count - 1)
        if dependency_count < 1:
            dependency_count = 1

        dependencies = [
            x.latest.id for x in context.packages[:dependency_count]
        ]
        dependants = context.packages[dependency_count:]
        for package in print_progress(dependants, len(dependants)):
            package.latest.dependencies.set(dependencies)

    def clear(self) -> None:
        print("Deleting existing package dependency relations")
        PackageVersion.dependencies.through.objects.all().delete()
