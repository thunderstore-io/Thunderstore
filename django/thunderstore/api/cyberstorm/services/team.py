from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from thunderstore.api import error_messages
from thunderstore.core.types import UserType
from thunderstore.repository.models import Namespace, Team
from thunderstore.repository.models.team import TeamMemberRole


def disband_team(user: UserType, team_name: str) -> None:
    teams = Team.objects.exclude(is_active=False)
    team = get_object_or_404(teams, name=team_name)

    if not team.can_user_access(user):
        raise PermissionDenied(error_messages.RESOURCE_DENIED_ERROR)

    if not team.can_user_disband(user):
        raise PermissionDenied(error_messages.ACTION_DENIED_ERROR)

    team.delete()


def create_team(user: UserType, team_name: str) -> Team:
    if Team.objects.filter(name=team_name).exists():
        raise ValidationError(error_messages.RESOURCE_EXISTS_ERROR)

    if Namespace.objects.filter(name=team_name).exists():
        raise ValidationError(error_messages.RESOURCE_EXISTS_ERROR)

    if getattr(user, "service_account", None) is not None:
        raise ValidationError(error_messages.ACTION_DENIED_ERROR)

    team = Team.objects.create(name=team_name)
    team.add_member(user=user, role=TeamMemberRole.owner)

    return team
