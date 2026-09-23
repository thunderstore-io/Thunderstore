from typing import List, Optional

from django.contrib.auth import get_user_model

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.repository.models import AsyncPackageSubmission, Namespace, Team
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
        User = get_user_model()
        users_and_roles = [
            (f"{MEMBER_USER_PREFIX}{team.pk}_owner", TeamMemberRole.owner),
            *[
                (
                    f"{MEMBER_USER_PREFIX}{team.pk}_member_{index}",
                    TeamMemberRole.member,
                )
                for index in range(EXTRA_MEMBER_COUNT)
            ],
        ]
        for username, role in users_and_roles:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            team.members.update_or_create(user=user, defaults={"role": role})

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
        generated_users = get_user_model().objects.filter(
            username__startswith=MEMBER_USER_PREFIX
        )
        print("Deleting test team member submissions...")
        AsyncPackageSubmission.objects.filter(owner__in=generated_users).delete()
        print("Deleting existing test team member users...")
        generated_users.delete()
