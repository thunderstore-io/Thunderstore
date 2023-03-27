from typing import List, Optional

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.core.management.commands.content.package import PackagePopulator
from thunderstore.repository.models import PackageWiki


class PackageWikiPopulator(ContentPopulator):
    model_cls = PackageWiki
    objs: Optional[List[PackageWiki]] = None
    name = "package wikis"

    def populate(self, context: ContentPopulatorContext) -> None:
        print(f"Populating {self.name}...")

        self.objs = [
            PackageWiki.get_for_package(package, create=True)
            for package in context.packages
        ]

    def update_context(self, context: ContentPopulatorContext) -> None:
        if self.objs is not None:
            context.package_wikis = self.objs
        else:
            context.package_wikis = [
                x
                for x in [
                    PackageWiki.get_for_package(package, create=False, dummy=False)
                    for package in context.packages
                ]
                if x is not None
            ]

    def clear(self) -> None:
        PackageWiki.objects.filter(
            package__name__startswith=PackagePopulator.name_prefix
        ).delete()
