import dataclasses
from typing import Any, Generator, List, Optional, Sequence

from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team, TeamMember
from thunderstore.repository.models.namespace import Namespace
from thunderstore.repository.models.team import TeamMemberRole


@dataclasses.dataclass
class CheckResult:
    check_pass: bool
    errors: Optional[List[Exception]]


class OpCheck:
    """OperationCheck"""

    def run_check(self, _: UserType) -> CheckResult:
        return CheckResult(
            check_pass=False, errors=[NotImplementedError("Check not implemented")]
        )


class TeamOpCheck(OpCheck):
    team: Team

    def __init__(self, team: Team):
        self.team = team


class TeamAccessCheck(TeamOpCheck):
    def run_check(self, user: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_access(user)
            return CheckResult(check_pass=True, errors=None)
        except Exception as e:
            return CheckResult(check_pass=False, errors=[e])


class TeamDisbandCheck(TeamOpCheck):
    def run_check(self, user: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_disband(user)
            return CheckResult(check_pass=True, errors=None)
        except Exception as e:
            return CheckResult(check_pass=False, errors=[e])


def _run_checks(
    agent: UserType, checks: Sequence[OpCheck]
) -> Generator[CheckResult, Any, None]:
    return (check.run_check(agent) for check in checks)


def run_checks(agent: UserType, checks: Sequence[OpCheck]) -> CheckResult:
    results = _run_checks(agent, checks)
    errors = []
    check_pass = True
    for entry in results:
        if entry.errors:
            errors += entry.errors
        if not entry.check_pass:
            check_pass = False
    return CheckResult(check_pass=check_pass, errors=errors)


@transaction.atomic
def disband_team(agent: UserType, team: Team) -> None:
    checks = [
        TeamAccessCheck(team),
        TeamDisbandCheck(team),
    ]
    if (check_result := run_checks(agent, checks)).check_pass:
        team.delete()
    else:
        raise check_result.errors


@transaction.atomic
def create_team(agent: UserType, team_name: str) -> Team:
    if not agent or not agent.is_authenticated or not agent.is_active:
        raise PermissionValidationError("Must be authenticated to create teams")
    if getattr(agent, "service_account", None) is not None:
        raise PermissionValidationError("Service accounts cannot create teams")
    if Team.objects.filter(name__iexact=team_name).exists():
        raise ValidationError("Team with this name already exists")
    if Namespace.objects.filter(name__iexact=team_name).exists():
        raise ValidationError("Namespace with this name already exists")

    team = Team.create(name=team_name)
    team.add_member(user=agent, role=TeamMemberRole.owner)
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
