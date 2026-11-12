from django.db.models import signals

from thunderstore.community.models import PackageListing
from thunderstore.community.utils import get_default_community
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class ListingPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package listings")

        # Disabling signals to avoid spamming cache clear calls
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.disconnect(
            PackageListing.post_delete, sender=PackageListing
        )

        # Ensure that we also populate packages in the default community.
        communities = list(context.communities)
        default_community = get_default_community()
        if default_community and default_community not in communities:
            communities.append(default_community)

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            for community in communities:
                package.get_or_create_package_listing(community)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.connect(PackageListing.post_delete, sender=PackageListing)

    def clear(self) -> None:
        print("Deleting existing package listings...")
        PackageListing.objects.all().delete()
