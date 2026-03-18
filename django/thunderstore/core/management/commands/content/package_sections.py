from thunderstore.community.models import PackageCategory, PackageListingSection
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class SectionPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package listing sections...")
        for community in print_progress(context.communities, len(context.communities)):

            def get_cat(slug):
                return PackageCategory.objects.get(community=community, slug=slug)

            # Define sections
            # Note: Higher priority value means the section is shown first (descending sort).
            sections_data = [
                {
                    "name": "Mods",
                    "slug": "mods",
                    "priority": 100,
                    "exclude": ["modpacks", "asset-replacements"],
                    "require": [],
                },
                {
                    "name": "Asset Replacements",
                    "slug": "asset-replacements",
                    "priority": 90,
                    "exclude": ["modpacks"],
                    "require": ["asset-replacements"],
                },
                {
                    "name": "Tools",
                    "slug": "tools",
                    "priority": 85,
                    "exclude": ["modpacks"],
                    "require": ["tools"],
                },
                {
                    "name": "APIs & Libraries",
                    "slug": "libraries",
                    "priority": 80,
                    "exclude": ["modpacks"],
                    "require": ["libraries"],
                },
                {
                    "name": "Modpacks",
                    "slug": "modpacks",
                    "priority": 70,
                    "exclude": [],
                    "require": ["modpacks"],
                },
            ]

            for s_data in sections_data:
                section, created = PackageListingSection.objects.get_or_create(
                    community=community,
                    slug=s_data["slug"],
                    defaults={
                        "name": s_data["name"],
                        "priority": s_data["priority"],
                    },
                )

                if created:
                    for ex_slug in s_data["exclude"]:
                        try:
                            cat = get_cat(ex_slug)
                            section.exclude_categories.add(cat)
                        except PackageCategory.DoesNotExist:
                            print(f"Warning: Category {ex_slug} not found for section {s_data['slug']}")

                    for req_slug in s_data["require"]:
                        try:
                            cat = get_cat(req_slug)
                            section.require_categories.add(cat)
                        except PackageCategory.DoesNotExist:
                            print(f"Warning: Category {req_slug} not found for section {s_data['slug']}")

    def clear(self) -> None:
        print("Deleting existing package listing sections...")
        PackageListingSection.objects.all().delete()
