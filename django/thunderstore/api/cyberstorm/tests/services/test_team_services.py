import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.services.team import (
    create_team,
    disband_team,
    remove_team_member,
)
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import Namespace, Team, TeamMember, TeamMemberRole


@pytest.mark.django_db
def test_disband_team_success(team_owner):
    team_pk = team_owner.team.pk
    disband_team(team_owner.user, team_owner.team.name)
    assert not Team.objects.filter(pk=team_pk).exists()


@pytest.mark.django_db
def test_disband_team_user_cannot_access_team(user):
    team = Team.objects.create(name="TestTeam")
    error_msg = "Must be a member to access team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        disband_team(user, team.name)


@pytest.mark.django_db
def test_disband_team_user_cannot_disband(team_member):
    error_msg = "Must be an owner to disband team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        disband_team(team_member.user, team_member.team.name)


@pytest.mark.django_db
def test_create_team_name_exists_in_team(user):
    Team.objects.create(name="existing_team")

    error_msg = "A team with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        create_team(user, "existing_team")


@pytest.mark.django_db
def test_create_team_name_exists_in_namespace(user):
    Namespace.objects.create(name="existing_namespace")

    error_msg = "A namespace with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        create_team(user, "existing_namespace")


@pytest.mark.django_db
def test_create_team_user_is_service_account(service_account):
    service_account_user = service_account.user

    error_msg = "Service accounts cannot create teams"
    with pytest.raises(PermissionValidationError, match=error_msg):
        create_team(service_account_user, "new_team")


@pytest.mark.django_db
def test_create_team_success(user):
    team_name = "new_team"
    team = create_team(user, team_name)

    assert Team.objects.filter(name=team_name).exists()
    assert team.name == team_name
    assert team.members.filter(user=user, role=TeamMemberRole.owner).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_remove_team_member_user_types(user_type: str, team_member):
    user = TestUserTypes.get_user_by_type(user_type)
    team_member_pk = team_member.pk

    user_type_result = {
        TestUserTypes.no_user: (False, PermissionValidationError),
        TestUserTypes.unauthenticated: (False, PermissionValidationError),
        TestUserTypes.regular_user: (True, None),
        TestUserTypes.deactivated_user: (False, PermissionValidationError),
        TestUserTypes.service_account: (False, PermissionValidationError),
        TestUserTypes.site_admin: (True, None),
        TestUserTypes.superuser: (True, None),
    }

    should_raise_error = user_type_result[user_type][0] is False

    if not user_type in [TestUserTypes.no_user, TestUserTypes.unauthenticated]:
        team_member.team.add_member(user=user, role=TeamMemberRole.owner)

    if should_raise_error:

        with pytest.raises(user_type_result[user_type][1]):
            remove_team_member(agent=user, team_member=team_member)
    else:
        remove_team_member(agent=user, team_member=team_member)
        assert not TeamMember.objects.filter(pk=team_member_pk).exists()


@pytest.mark.django_db
def test_remove_team_member_success(team_owner, user):
    team_owner.team.add_member(user=user, role=TeamMemberRole.member)
    team_member = TeamMember.objects.get(user=user)

    remove_team_member(agent=team_owner.user, team_member=team_member)
    assert not TeamMember.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_remove_team_member_user_cannot_access(user, team_member):
    error_msg = "Must be a member to access team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        remove_team_member(agent=user, team_member=team_member)


@pytest.mark.django_db
def test_remove_team_member_user_cannot_manage_members(user, team):
    user2 = UserFactory()

    team.add_member(user=user, role=TeamMemberRole.member)
    team.add_member(user=user2, role=TeamMemberRole.member)
    team_member = TeamMember.objects.get(user=user2)

    error_msg = "Must be an owner to manage team members"
    with pytest.raises(PermissionValidationError, match=error_msg):
        remove_team_member(agent=user, team_member=team_member)


@pytest.mark.django_db
def test_remove_team_member_cannot_remove_last_owner(team_owner):
    with pytest.raises(ValidationError, match="Cannot remove last owner from team"):
        remove_team_member(agent=team_owner.user, team_member=team_owner)
