from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Namespace, Team
from thunderstore.repository.models.team import TeamMemberRole


@transaction.atomic
def disband_team(user: UserType, team_name: str) -> None:
    teams = Team.objects.exclude(is_active=False)
    team = get_object_or_404(teams, name=team_name)
    team.ensure_user_can_access(user)
    team.ensure_user_can_disband(user)
    team.delete()


@transaction.atomic
def create_team(user: UserType, team_name: str) -> Team:
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionValidationError("Must be authenticated to create teams")
    if getattr(user, "service_account", None) is not None:
        raise PermissionValidationError("Service accounts cannot create teams")
    if Team.objects.filter(name=team_name).exists():
        raise ValidationError("A team with the provided name already exists")
    if Namespace.objects.filter(name=team_name).exists():
        raise ValidationError("A namespace with the provided name already exists")

    team = Team.objects.create(name=team_name)
    team.add_member(user=user, role=TeamMemberRole.owner)
    return team


@transaction.atomic
def update_team(agent: UserType, team: Team, donation_link: str) -> Team:
    team.ensure_user_can_access(agent)
    team.ensure_user_can_edit_info(agent)

    team.donation_link = donation_link
    team.save()

    return team
