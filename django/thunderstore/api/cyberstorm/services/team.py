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


@dataclasses.dataclass
class CheckResult:
    success: bool
    error: Optional[ValidationError] = None

    def as_exception(self) -> Union[ValidationError, Exception]:
        return (
            self.error
            if self.error
            else ValidationError("Check failed without message")
        )


class OpCheck:
    def run_check(self, agent: UserType) -> CheckResult:
        return CheckResult(
            success=False, error=ValidationError("Check not implemented")
        )


@dataclasses.dataclass
class TeamOpCheck(OpCheck):
    team: Team


class PermissionTeamAccess(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_access(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


class PermissionTeamDisband(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_disband(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


class PermissionTeamEdit(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_edit_info(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


class PermissionTeamManageMembers(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_user_can_manage_members(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


@dataclasses.dataclass
class CheckAgentCanRemoveTeamMember(OpCheck):
    member: TeamMember

    def run_check(self, agent: UserType) -> CheckResult:
        if agent != self.member.user:
            return PermissionTeamManageMembers(team=self.member.team).run_check(agent)
        else:
            return CheckResult(success=True)


@dataclasses.dataclass
class CheckTeamMemberCanBeRemoved(OpCheck):
    member: TeamMember

    def run_check(self, _: UserType) -> CheckResult:
        try:
            self.member.team.ensure_member_can_be_removed(self.member)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


@dataclasses.dataclass
class CheckTeamNameFree(OpCheck):
    team_name: str

    def run_check(self, agent: UserType) -> CheckResult:
        if Team.objects.filter(name__iexact=self.team_name).exists():
            return CheckResult(
                success=False,
                error=ValidationError("Team with this name already exists"),
            )
        else:
            return CheckResult(success=True)


@dataclasses.dataclass
class CheckNamespaceNameFree(OpCheck):
    namespace_name: str

    def run_check(self, agent: UserType) -> CheckResult:
        if Namespace.objects.filter(name__iexact=self.namespace_name).exists():
            return CheckResult(
                success=False,
                error=ValidationError("Namespace with this name already exists"),
            )
        else:
            return CheckResult(success=True)


class CheckAgentIsAuthenticated(OpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        if not agent or not agent.is_authenticated or not agent.is_active:
            return CheckResult(
                success=False,
                error=PermissionValidationError("User must be authenticated"),
            )
        else:
            return CheckResult(success=True)


class CheckAgentNotServiceAccount(OpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        if getattr(agent, "service_account", None) is not None:
            return CheckResult(
                success=False,
                error=PermissionValidationError(
                    "Service accounts cannot perform this action"
                ),
            )
        else:
            return CheckResult(success=True)


class CheckTeamServiceAccountCreationPermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_can_create_service_account(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


class CheckTeamServiceAccountDeletePermission(TeamOpCheck):
    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.team.ensure_can_delete_service_account(agent)
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


@dataclasses.dataclass
class CheckTeamMemberRoleCanChange(OpCheck):
    member: TeamMember
    target_role: str

    def run_check(self, agent: UserType) -> CheckResult:
        try:
            self.member.team.ensure_member_role_can_be_changed(
                member=self.member,
                new_role=self.target_role,
            )
            return CheckResult(success=True)
        except ValidationError as e:
            return CheckResult(success=False, error=e)


def run_checks(agent: UserType, checks: Sequence[Union[OpCheck, None]]) -> CheckResult:
    results = (check.run_check(agent) for check in checks if check)
    for entry in results:
        if not entry.success:
            return entry
    return CheckResult(success=True)


@transaction.atomic
def disband_team(agent: UserType, team: Team) -> None:
    checks = [
        PermissionTeamAccess(team=team),
        PermissionTeamDisband(team=team),
    ]
    if (check_result := run_checks(agent, checks)).success:
        team.delete()
    else:
        raise check_result.as_exception()


@transaction.atomic
def create_team(agent: UserType, team_name: str) -> Team:
    checks = [
        CheckAgentIsAuthenticated(),
        CheckAgentNotServiceAccount(),
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
        PermissionTeamAccess(team=team),
        PermissionTeamEdit(team=team),
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
        CheckAgentCanRemoveTeamMember(member=member),
        CheckTeamMemberCanBeRemoved(member=member),
    ]
    if (result := run_checks(agent, checks)).success:
        member.delete()
    else:
        raise result.as_exception()


@transaction.atomic
def create_service_account(agent: UserType, team: Team, nickname: str):
    checks = [
        PermissionTeamAccess(team=team),
        CheckTeamServiceAccountCreationPermission(team=team),
    ]
    if (result := run_checks(agent, checks)).success:
        service_account, token = ServiceAccount.create(
            owner=team,
            nickname=nickname,
            creator=agent,
        )
        return service_account, token
    else:
        raise result.as_exception()


@transaction.atomic
def delete_service_account(agent: UserType, service_account: ServiceAccount):
    team = service_account.owner
    checks = [
        PermissionTeamAccess(team=team),
        CheckTeamServiceAccountDeletePermission(team=team),
    ]
    if (result := run_checks(agent, checks)).success:
        return service_account.delete()
    else:
        raise result.as_exception()


@transaction.atomic
def update_team_member(
    agent: UserType,
    team_member: TeamMember,
    role: str,
) -> TeamMember:
    team = team_member.team

    checks = [
        PermissionTeamAccess(team=team),
        PermissionTeamManageMembers(team=team),
        CheckTeamMemberRoleCanChange(member=team_member, target_role=role),
    ]

    if (result := run_checks(agent, checks)).success:
        team_member.role = role
        team_member.save()
        return team_member
    else:
        raise result.as_exception()
