import pytest
from django.core.exceptions import ValidationError
from django.http import Http404

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.services import team as team_services
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.repository.models import Namespace, Team, TeamMemberRole


@pytest.mark.django_db
def test_disband_team_success(team_owner):
    team_pk = team_owner.team.pk
    team_services.disband_team(team_owner.user, team_owner.team.name)
    assert not Team.objects.filter(pk=team_pk).exists()


@pytest.mark.django_db
def test_disband_team_team_not_found(user):
    with pytest.raises(Http404):
        team_services.disband_team(user, "NonExistentTeam")


@pytest.mark.django_db
def test_disband_team_user_cannot_access_team(user):
    team = Team.objects.create(name="TestTeam")
    with pytest.raises(ValidationError, match="Must be a member to access team"):
        team_services.disband_team(user, team.name)


@pytest.mark.django_db
def test_disband_team_user_cannot_disband(team_member):
    with pytest.raises(ValidationError, match="Must be an owner to disband team"):
        team_services.disband_team(team_member.user, team_member.team.name)


@pytest.mark.django_db
def test_create_team_name_exists_in_team(user):
    Team.objects.create(name="existing_team")

    error_msg = "A team with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(user, "existing_team")


@pytest.mark.django_db
def test_create_team_name_exists_in_namespace(user):
    Namespace.objects.create(name="existing_namespace")

    error_msg = "A namespace with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(user, "existing_namespace")


@pytest.mark.django_db
def test_create_team_user_is_service_account(service_account):
    service_account_user = service_account.user

    error_msg = "Service accounts cannot create teams"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(service_account_user, "new_team")


@pytest.mark.django_db
def test_create_team_success(user):
    team_name = "new_team"
    team = team_services.create_team(user, team_name)

    assert Team.objects.filter(name=team_name).exists()
    assert team.name == team_name
    assert team.members.filter(user=user, role=TeamMemberRole.owner).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_update_team_member_user_roles(user_type, team_member):
    user = TestUserTypes.get_user_by_type(user_type)
    team = team_member.team

    if user_type not in TestUserTypes.fake_users():
        team.add_member(user=user, role=TeamMemberRole.owner)

    expected_result_mapping = {
        TestUserTypes.no_user: (False, PermissionValidationError),
        TestUserTypes.unauthenticated: (False, PermissionValidationError),
        TestUserTypes.regular_user: (True, None),
        TestUserTypes.deactivated_user: (False, PermissionValidationError),
        TestUserTypes.service_account: (False, PermissionValidationError),
        TestUserTypes.site_admin: (True, None),
        TestUserTypes.superuser: (True, None),
    }

    should_raise = expected_result_mapping[user_type][0] is False

    if should_raise:
        with pytest.raises(expected_result_mapping[user_type][1]):
            team_services.update_team_member(user, team_member, TeamMemberRole.owner)
    else:
        update_user = team_services.update_team_member(
            user, team_member, TeamMemberRole.owner
        )
        assert update_user.role == TeamMemberRole.owner


@pytest.mark.django_db
def test_update_team_member_user_cannot_access_team(user, team_member):
    error_msg = "Must be a member to access team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team_member(user, team_member, TeamMemberRole.owner)


@pytest.mark.django_db
def test_update_team_member_user_cannot_manage_members(team_member, user):
    team = team_member.team
    team.add_member(user=user, role=TeamMemberRole.member)

    error_msg = "Must be an owner to manage team members"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team_member(user, team_member, TeamMemberRole.owner)


@pytest.mark.django_db
def test_update_team_member_invalid_role(team_member, user):
    team = team_member.team
    team.add_member(user=user, role=TeamMemberRole.owner)

    with pytest.raises(ValidationError, match="New role is invalid"):
        team_services.update_team_member(user, team_member, "invalid_role")


@pytest.mark.django_db
def test_update_team_member_success(team_member, user):
    team = team_member.team
    team.add_member(user=user, role=TeamMemberRole.owner)

    assert team_member.role == TeamMemberRole.member

    updated_member = team_services.update_team_member(
        user, team_member, TeamMemberRole.owner
    )

    assert updated_member.role == TeamMemberRole.owner


@pytest.mark.django_db
def test_update_team_member_cannot_remove_last_owner(team_owner):
    error_msg = "Cannot remove last owner from team"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.update_team_member(
            team_owner.user, team_owner, TeamMemberRole.member
        )
