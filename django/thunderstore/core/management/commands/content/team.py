from typing import List, Optional

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.models import Namespace, Team
from thunderstore.utils.iterators import print_progress


class TeamPopulator(ContentPopulator):
    teams: Optional[List[Team]] = None
    name_prefix = "Test_Team_"

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating teams...")

        last = last_team.pk if (last_team := Team.objects.last()) else 0

        existing = list(
            Team.objects.filter(name__startswith=self.name_prefix)[: context.team_count]
        )
        remainder = context.team_count - len(existing)

        self.teams = existing + [
            Team.create(name=f"{self.name_prefix}{last + i}")
            for i in print_progress(range(remainder), remainder)
        ]

    def update_context(self, context) -> None:
        if self.teams is not None:
            context.teams = self.teams
        else:
            context.teams = Team.objects.filter(name__startswith=self.name_prefix)[
                : context.team_count
            ]

    def clear(self) -> None:
        print("Deleting existing teams...")
        Team.objects.all().delete()
        print("Deleting existing namespaces...")
        Namespace.objects.all().delete()
