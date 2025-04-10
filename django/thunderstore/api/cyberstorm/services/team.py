from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from thunderstore.api import error_messages
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team


def disband_team(user: UserType, team_name: str) -> None:
    teams = Team.objects.exclude(is_active=False)
    team = get_object_or_404(teams, name=team_name)

    if not team.can_user_access(user):
        raise PermissionDenied(error_messages.RESOURCE_DENIED_ERROR)

    if not team.can_user_disband(user):
        raise PermissionDenied(error_messages.ACTION_DENIED_ERROR)

    team.delete()
