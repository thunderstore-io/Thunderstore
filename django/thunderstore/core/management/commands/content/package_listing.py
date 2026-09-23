from typing import List

from django.db.models import signals

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
    package_identity,
    seeded_random,
)
from thunderstore.utils.iterators import print_progress

# Probability that a generated listing is flagged NSFW so the NSFW badge shows
# up in the UI on a portion of the test data.
NSFW_PROBABILITY = 0.15


class ListingPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package listings")

        # Disabling signals to avoid spamming cache clear calls
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.disconnect(
            PackageListing.post_delete, sender=PackageListing
        )

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            for community in context.communities:
                listing, _created = PackageListing.objects.get_or_create(
                    package=package,
                    community=community,
                )
                self.assign_categories(context, listing, community)
                self.assign_nsfw(listing)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.connect(PackageListing.post_delete, sender=PackageListing)

    def assign_categories(
        self,
        context: ContentPopulatorContext,
        listing: PackageListing,
        community,
    ) -> None:
        community_categories = context.categories.get(community.pk, [])
        if not community_categories:
            return
        chosen = desired_listing_categories(
            listing.package, community, community_categories
        )
        chosen_ids = {category.pk for category in chosen}
        current_ids = set(listing.categories.values_list("pk", flat=True))
        if current_ids != chosen_ids:
            listing.categories.set(chosen)

    def assign_nsfw(self, listing: PackageListing) -> None:
        has_nsfw_content = desired_nsfw(listing.package, listing.community)
        if listing.has_nsfw_content != has_nsfw_content:
            listing.has_nsfw_content = has_nsfw_content
            listing.save(update_fields=("has_nsfw_content",))

    def clear(self) -> None:
        print("Deleting existing package listings...")
        PackageListing.objects.all().delete()


def desired_listing_categories(package, community, categories) -> List[PackageCategory]:
    # Allow 0 so some listings end up with no categories.
    ordered = sorted(categories, key=lambda category: (category.slug, category.pk))
    rng = seeded_random("categories", package_identity(package), community.identifier)
    count = rng.randint(0, min(3, len(ordered)))
    if not count:
        return []
    return rng.sample(ordered, count)


def desired_nsfw(package, community) -> bool:
    rng = seeded_random("nsfw", package_identity(package), community.identifier)
    return rng.random() < NSFW_PROBABILITY
