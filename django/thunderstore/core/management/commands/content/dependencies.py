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
        dependencies = [
            x.latest.id for x in context.packages[: context.dependency_count]
        ]
        dependants = context.packages[context.dependency_count :]
        for package in print_progress(dependants, len(dependants)):
            package.latest.dependencies.set(dependencies)

    def clear(self) -> None:
        print("Deleting existing package dependency relations")
        PackageVersion.dependencies.through.objects.all().delete()
