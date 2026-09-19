from typing import List, Optional

from django.contrib.auth import get_user_model

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.models import Namespace, Team
from thunderstore.repository.models.team import TeamMemberRole
from thunderstore.utils.iterators import print_progress

MEMBER_USER_PREFIX = "Test_TeamMember_"
EXTRA_MEMBER_COUNT = 2


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

        print("Populating team members...")
        for team in print_progress(self.teams, len(self.teams)):
            self._ensure_team_members(team)

    def _ensure_team_members(self, team: Team) -> None:
        # Ignore service-account-only membership so we still seed an owner
        # and real users for teams that only have service accounts.
        if team.members.real_users().exists():
            return

        User = get_user_model()
        owner_username = f"{MEMBER_USER_PREFIX}{team.pk}_owner"
        owner, _ = User.objects.get_or_create(
            username=owner_username,
            defaults={"email": f"{owner_username}@example.com"},
        )
        team.add_member(owner, role=TeamMemberRole.owner)

        for index in range(EXTRA_MEMBER_COUNT):
            member_username = f"{MEMBER_USER_PREFIX}{team.pk}_member_{index}"
            member, _ = User.objects.get_or_create(
                username=member_username,
                defaults={"email": f"{member_username}@example.com"},
            )
            team.add_member(member, role=TeamMemberRole.member)

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
