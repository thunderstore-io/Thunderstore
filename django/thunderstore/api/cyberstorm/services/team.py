from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Namespace, Team
from thunderstore.repository.models.team import TeamMemberRole


@transaction.atomic
def disband_team(agent: UserType, team: Team) -> None:
    team.ensure_user_can_access(agent)
    team.ensure_user_can_disband(agent)
    team.delete()


@transaction.atomic
def create_team(agent: UserType, team_name: str) -> Team:
    if not agent or not agent.is_authenticated or not agent.is_active:
        raise PermissionValidationError("Must be authenticated to create teams")
    if getattr(agent, "service_account", None) is not None:
        raise PermissionValidationError("Service accounts cannot create teams")
    if Team.objects.filter(name=team_name).exists():
        raise ValidationError("A team with the provided name already exists")
    if Namespace.objects.filter(name=team_name).exists():
        raise ValidationError("A namespace with the provided name already exists")

    team = Team.objects.create(name=team_name)
    team.add_member(user=agent, role=TeamMemberRole.owner)
    return team
