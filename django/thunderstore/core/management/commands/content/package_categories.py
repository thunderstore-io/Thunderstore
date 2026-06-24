from typing import List

from thunderstore.community.models import PackageCategory
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class CategoryPopulator(ContentPopulator):
    categories = [
        "Mods",
        "Modpacks",
        "Tools",
        "Libraries",
        "Misc",
        "Audio",
        "BepInEx",
        "MelonLoader",
        "Suits",
        "Boombox Music",
        "TV Videos",
        "Posters",
        "Equipment",
        "Items",
        "Monsters",
        "Moons",
        "Interiors",
        "Furniture",
        "Vehicles",
        "Client-side",
        "Server-side",
        "Cosmetics",
        "Asset Replacements",
        "Translations",
        "Emotes",
        "Weather",
        "Hazards",
        "Bug Fixes",
        "Performance",
        "Tweaks & Quality Of Life",
    ]

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package categories...")
        for community in print_progress(context.communities, len(context.communities)):
            for name in self.categories:
                slug = name.lower().replace(" ", "-").replace("&", "").replace("--", "-")
                PackageCategory.objects.get_or_create(
                    community=community,
                    name=name,
                    defaults={"slug": slug},
                )

    def clear(self) -> None:
        print("Deleting existing package categories...")
        PackageCategory.objects.all().delete()
