import dataclasses
from typing import List, Optional, Sequence, Union

from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team, TeamMember
from thunderstore.repository.models.namespace import Namespace
from thunderstore.repository.models.team import TeamMemberRole


class CheckException(ValidationError):
    pass


@dataclasses.dataclass
class CheckResult:
    success: bool
    errors: Optional[List[Exception]]

    def as_exception(self) -> Union[CheckException, ValidationError, Exception]:
        if len(self.errors) == 1:
            return self.errors[0]
        else:
            return CheckException(message=self.errors)


class OpCheck:
    def run_check(self, agent: UserType) -> CheckResult:
        return CheckResult(
            success=False, errors=[ValidationError("Check not implemented")]
        )


@dataclasses.dataclass
class TeamOpCheck(OpCheck):
    team: Team


class CheckTeamAccessPermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_access(agent)
            return CheckResult(success=True, errors=None)
        except Exception as e:
            return CheckResult(success=False, errors=[e])


class CheckTeamDisbandPermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_disband(agent)
            return CheckResult(success=True, errors=None)
        except Exception as e:
            return CheckResult(success=False, errors=[e])


class CheckTeamEditPermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_edit_info(agent)
            return CheckResult(success=True, errors=None)
        except Exception as e:
            return CheckResult(success=False, errors=[e])


class CheckTeamMemberManagePermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_manage_members(agent)
            return CheckResult(success=True, errors=None)
        except Exception as e:
            return CheckResult(success=False, errors=[e])


@dataclasses.dataclass
class CheckTeamMemberCanBeRemoved(OpCheck):
    member: TeamMember

    def run_check(self, _: UserType) -> CheckResult:
        try:
            self.member.team.ensure_member_can_be_removed(self.member)
            return CheckResult(success=True, errors=None)
        except Exception as e:
            return CheckResult(success=False, errors=[e])


@dataclasses.dataclass
class CheckTeamNameFree(OpCheck):
    team_name: str

    def run_check(self, agent: UserType) -> CheckResult:
        if Team.objects.filter(name__iexact=self.team_name).exists():
            return CheckResult(
                success=False,
                errors=[ValidationError("Team with this name already exists")],
            )
        else:
            return CheckResult(success=True, errors=None)


@dataclasses.dataclass
class CheckNamespaceNameFree(OpCheck):
    namespace_name: str

    def run_check(self, agent: UserType) -> CheckResult:
        if Namespace.objects.filter(name__iexact=self.namespace_name).exists():
            return CheckResult(
                success=False,
                errors=[ValidationError("Namespace with this name already exists")],
            )
        else:
            return CheckResult(success=True, errors=None)


class CheckUserIsAuthenticated(OpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        if not agent or not agent.is_authenticated or not agent.is_active:
            return CheckResult(
                success=False,
                errors=[PermissionValidationError("User must be authenticated")],
            )
        else:
            return CheckResult(success=True, errors=None)


class CheckUserIsNotServiceAccount(OpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        if getattr(agent, "service_account", None) is not None:
            raise PermissionValidationError(
                "Service accounts cannot perform this action"
            )


def run_checks(agent: UserType, checks: Sequence[Union[OpCheck, None]]) -> CheckResult:
    results = (check.run_check(agent) for check in checks if check)
    errors = []
    check_pass = True
    for entry in results:
        if entry.errors:
            errors += entry.errors
        if not entry.success:
            check_pass = False
    return CheckResult(success=check_pass, errors=errors)


@transaction.atomic
def disband_team(agent: UserType, team: Team) -> None:
    checks = [
        CheckTeamAccessPermission(team=team),
        CheckTeamDisbandPermission(team=team),
    ]
    if (check_result := run_checks(agent, checks)).success:
        team.delete()
    else:
        raise check_result.as_exception()


@transaction.atomic
def create_team(agent: UserType, team_name: str) -> Team:
    checks = [
        CheckUserIsAuthenticated(),
        CheckUserIsNotServiceAccount(),
        CheckTeamNameFree(team_name=team_name),
        CheckNamespaceNameFree(namespace_name=team_name),
    ]
    if (result := run_checks(agent, checks)).success:
        team = Team.create(name=team_name)
        team.add_member(user=agent, role=TeamMemberRole.owner)
        return team
    else:
        raise result.as_exception()


@transaction.atomic
def update_team(agent: UserType, team: Team, donation_link: str) -> Team:
    checks = [
        CheckTeamAccessPermission(team=team),
        CheckTeamEditPermission(team=team),
    ]
    if (result := run_checks(agent, checks)).success:
        team.donation_link = donation_link
        team.save()
        return team
    else:
        raise result.as_exception()


@transaction.atomic
def remove_team_member(agent: UserType, member: TeamMember) -> None:
    checks = [
        CheckTeamMemberManagePermission(team=member.team)
        if member.user != agent
        else None,
        CheckTeamMemberCanBeRemoved(member=member),
    ]
    if (result := run_checks(agent, checks)).success:
        member.delete()
    else:
        raise result.as_exception()


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
