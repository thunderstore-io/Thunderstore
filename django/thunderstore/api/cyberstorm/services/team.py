from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from thunderstore.account.models import ServiceAccount
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Namespace, Team, TeamMember
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


@transaction.atomic
def remove_team_member(agent: UserType, member: TeamMember) -> None:
    if member.user != agent:
        member.team.ensure_user_can_manage_members(agent)
    member.team.ensure_member_can_be_removed(member)
    member.delete()


@transaction.atomic
def create_service_account(agent: UserType, team: Team, nickname: str):
    team.ensure_user_can_access(agent)
    team.ensure_can_create_service_account(agent)

    service_account, token = ServiceAccount.create(
        owner=team,
        nickname=nickname,
        creator=agent,
    )

    return service_account, token


@transaction.atomic
def delete_service_account(agent: UserType, service_account: ServiceAccount):
    team = service_account.owner
    team.ensure_user_can_access(agent)
    team.ensure_can_delete_service_account(agent)
    return service_account.delete()


@transaction.atomic
def update_team_member(
    agent: UserType,
    team_member: TeamMember,
    role: str,
) -> TeamMember:
    team = team_member.team

    team.ensure_user_can_access(agent)
    team.ensure_user_can_manage_members(agent)
    team.ensure_member_role_can_be_changed(team_member, role)

    team_member.role = role
    team_member.save()

    return team_member
