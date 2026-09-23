from typing import Dict, List, Optional

from thunderstore.community.models import Community
from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class CommunityPopulator(ContentPopulator):
    communities: Optional[List[Community]] = None
    identifier_prefix = "test-community-"
    name_prefix = "Test Community "

    def identifier_suffix(self, identifier: str) -> Optional[int]:
        if not identifier.startswith(self.identifier_prefix):
            return None
        raw = identifier[len(self.identifier_prefix) :]
        if not raw.isdigit() or str(int(raw)) != raw:
            return None
        return int(raw)

    def expected_identifiers(self, count: int) -> List[str]:
        return [f"{self.identifier_prefix}{suffix}" for suffix in range(1, count + 1)]

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating communities...")

        expected_suffixes = set(range(1, context.community_count + 1))
        kept: Dict[int, Community] = {}
        for community in Community.objects.filter(
            identifier__startswith=self.identifier_prefix
        ):
            suffix = self.identifier_suffix(community.identifier)
            if suffix in expected_suffixes:
                kept[suffix] = community

        missing = [
            suffix
            for suffix in range(1, context.community_count + 1)
            if suffix not in kept
        ]
        if missing:
            for suffix in print_progress(missing, len(missing)):
                kept[suffix] = Community.objects.create(
                    name=f"{self.name_prefix}{suffix}",
                    identifier=f"{self.identifier_prefix}{suffix}",
                )

        self.communities = [
            kept[suffix] for suffix in range(1, context.community_count + 1)
        ]

    def communities_for_context(self, count: int) -> List[Community]:
        expected = self.expected_identifiers(count)
        by_identifier = {
            community.identifier: community
            for community in Community.objects.filter(identifier__in=expected)
        }
        communities = [
            by_identifier[identifier]
            for identifier in expected
            if identifier in by_identifier
        ]
        if len(communities) >= count:
            return communities

        seen = {community.pk for community in communities}
        extras = Community.objects.filter(name__startswith=self.name_prefix)
        if seen:
            extras = extras.exclude(pk__in=seen)
        for community in extras:
            communities.append(community)
            if len(communities) >= count:
                break
        return communities

    def update_context(self, context) -> None:
        if self.communities is not None:
            context.communities = self.communities
        else:
            context.communities = self.communities_for_context(context.community_count)

    def clear(self) -> None:
        print("Deleting existing test communities...")
        Community.objects.filter(name__startswith=self.name_prefix).delete()
