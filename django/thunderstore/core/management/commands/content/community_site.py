from django.contrib.sites.models import Site

from thunderstore.community.models import CommunitySite
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)


class CommunitySitePopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating community sites...")

        for community in context.communities:
            community_site = CommunitySite.objects.filter(community=community).first()
            if community_site:
                continue
            CommunitySite.objects.create(
                community=community,
                site=Site.objects.get_or_create(
                    name="Thunderstore",
                    domain=f"{community.identifier}.thunderstore.localhost",
                )[0],
            )

    def update_context(self, context) -> None:
        pass

    def clear(self) -> None:
        pass
