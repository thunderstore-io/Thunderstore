from typing import List, Optional

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
    dummy_markdown,
)
from thunderstore.core.management.commands.content.package import PackagePopulator
from thunderstore.wiki.factories import WikiPageFactory
from thunderstore.wiki.models import WikiPage


class PackageWikiPagePopulator(ContentPopulator):
    model_cls = WikiPage
    objs: Optional[List[WikiPage]] = None
    name = "package wiki pages"
    title_prefix = "Test Page "

    def populate(self, context: ContentPopulatorContext) -> None:
        print(f"Populating {self.name}...")

        self.objs = []
        for package_wiki in context.package_wikis:
            existing = package_wiki.wiki.pages.filter(
                title__startswith=self.title_prefix
            ).count()
            for i in range(context.wiki_page_count - existing):
                self.objs.append(
                    WikiPageFactory.create(
                        wiki=package_wiki.wiki,
                        title=f"{self.title_prefix}{i}",
                        markdown_content=dummy_markdown(),
                    )
                )

    def update_context(self, context: ContentPopulatorContext) -> None:
        if self.objs is not None:
            context.package_wiki_pages = self.objs
        else:
            context.package_wikis = WikiPage.objects.filter(
                wiki__package_wiki__package__name__startswith=PackagePopulator.name_prefix,
                title__startswith=self.title_prefix,
            )

    def clear(self) -> None:
        WikiPage.objects.filter(
            wiki__package_wiki__package__name__startswith=PackagePopulator.name_prefix,
            title__startswith=self.title_prefix,
        ).delete()
