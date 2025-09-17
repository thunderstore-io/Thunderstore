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
def test_update_team_success(team_owner):
    team = team_owner.team
    new_donation_link = "https://example.com/donate"
    updated_team = team_services.update_team(
        agent=team_owner.user, team=team, donation_link=new_donation_link
    )

    assert updated_team.donation_link == new_donation_link


@pytest.mark.django_db
def test_update_team_user_cannot_access(user, team):
    new_donation_link = "https://example.com/donate"

    error_msg = "Must be a member to access team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team(
            agent=user, team=team, donation_link=new_donation_link
        )


@pytest.mark.django_db
def test_update_team_user_cannot_edit_info(team_member):
    new_donation_link = "https://example.com/donate"

    error_msg = "Must be an owner to edit team info"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team(
            agent=team_member.user,
            team=team_member.team,
            donation_link=new_donation_link,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_create_service_account_user_types(user_type: str, team):
    user = TestUserTypes.get_user_by_type(user_type)

    user_type_result = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }

    should_raise_error = user_type_result[user_type] is False

    if user_type not in [TestUserTypes.no_user, TestUserTypes.unauthenticated]:
        team.add_member(user=user, role=TeamMemberRole.owner)

    if should_raise_error:
        with pytest.raises(PermissionValidationError):
            team_services.create_service_account(user, team, "TestServiceAccount")
    else:
        service_account, token = team_services.create_service_account(
            user, team, "TestServiceAccount"
        )
        assert service_account.owner == team
        assert service_account.nickname == "TestServiceAccount"
        assert token is not None
        assert token.startswith("tss_")


@pytest.mark.django_db
def test_create_service_account_not_owner(team_member):
    nickname = "TestServiceAccount"
    error_msg = "Must be an owner to create a service account"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.create_service_account(
            team_member.user, team_member.team, nickname
        )


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_delete_service_account_user_types(user_type: str, service_account):
    user = TestUserTypes.get_user_by_type(user_type)

    user_type_result = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }

    should_raise_error = user_type_result[user_type] is False
    team = service_account.owner

    if user_type not in [TestUserTypes.no_user, TestUserTypes.unauthenticated]:
        team.add_member(user=user, role=TeamMemberRole.owner)

    if should_raise_error:
        with pytest.raises(PermissionValidationError):
            team_services.delete_service_account(user, service_account)
    else:
        team_services.delete_service_account(user, service_account)
        assert service_account.pk is None


@pytest.mark.django_db
def test_delete_service_account_not_owner(service_account):
    user = UserFactory()
    service_account.owner.add_member(user=user, role=TeamMemberRole.member)
    error_msg = "Must be an owner to delete a service account"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.delete_service_account(user, service_account)

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
