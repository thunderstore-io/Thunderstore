from typing import Dict, List, Optional

from django.utils.text import slugify

from thunderstore.community.models import PackageCategory
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.core.management.commands.content.community import CommunityPopulator
from thunderstore.utils.iterators import print_progress

CATEGORY_NAMES = [
    "Mods",
    "Tools",
    "Libraries",
    "Audio",
    "Skins",
    "Tweaks",
    "Client-side",
    "Server-side",
    "Modpacks",
    "Language",
    "Misc",
]


class CategoryPopulator(ContentPopulator):
    categories: Optional[Dict[int, List[PackageCategory]]] = None
    name_prefix = CommunityPopulator.name_prefix

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package categories...")

        result: Dict[int, List[PackageCategory]] = {}
        for community in print_progress(context.communities, len(context.communities)):
            community_categories = []
            for name in CATEGORY_NAMES:
                category, _ = PackageCategory.objects.get_or_create(
                    community=community,
                    slug=slugify(name),
                    defaults={"name": name},
                )
                community_categories.append(category)
            result[community.pk] = community_categories

        self.categories = result

    def update_context(self, context: ContentPopulatorContext) -> None:
        if self.categories is not None:
            context.categories = self.categories
        else:
            context.categories = {
                community.pk: list(community.package_categories.all())
                for community in context.communities
            }

    def clear(self) -> None:
        print("Deleting existing package categories...")
        PackageCategory.objects.filter(
            community__name__startswith=self.name_prefix
        ).delete()
