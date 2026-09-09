import random

from django.db.models import signals

from thunderstore.community.models import PackageListing
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
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
                listing = package.get_or_create_package_listing(community)
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
        # Allow 0 so some listings end up with no categories (and, combined with
        # the probabilistic pinned/deprecated/nsfw tags, some with neither).
        count = random.randint(0, min(3, len(community_categories)))
        listing.categories.set(random.sample(community_categories, count))

    def assign_nsfw(self, listing: PackageListing) -> None:
        has_nsfw_content = random.random() < NSFW_PROBABILITY
        if listing.has_nsfw_content != has_nsfw_content:
            listing.has_nsfw_content = has_nsfw_content
            listing.save(update_fields=("has_nsfw_content",))

    def clear(self) -> None:
        print("Deleting existing package listings...")
        PackageListing.objects.all().delete()
