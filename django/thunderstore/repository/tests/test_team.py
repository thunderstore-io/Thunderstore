from typing import Optional

import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.account.factories import ServiceAccountFactory
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import TeamFactory, TeamMemberFactory
from thunderstore.repository.models import (
    Package,
    Team,
    TeamMember,
    TeamMemberRole,
    strip_unsupported_characters,
)


@pytest.mark.parametrize(
    "role, expected",
    [
        ["owner", True],
        ["member", True],
        [None, False],
    ],
)
@pytest.mark.django_db
def test_team_can_user_upload(user, role, expected) -> None:
    team = TeamFactory.create()
    if role:
        TeamMemberFactory.create(
            user=user,
            team=team,
            role=role,
        )
    assert team.can_user_upload(user) == expected


@pytest.mark.parametrize(
    "name, should_fail",
    (
        ("SomeAuthor", False),
        ("Some-Author", True),
        ("Som3-Auth0r", True),
        ("Som3_Auth0r", False),
        ("Some.Author", True),
        ("Some@Author", True),
        ("_someAuthor_", True),
        ("_someAuthor", True),
        ("someAuthor_", True),
        ("_", True),
    ),
)
@pytest.mark.django_db
def test_team_create(name: str, should_fail: bool) -> None:
    if should_fail:
        with pytest.raises(ValidationError):
            Team.objects.create(name=name)
    else:
        team = Team.objects.create(name=name)
        assert team.name == name


@pytest.mark.django_db
@pytest.mark.parametrize(
    "username, expected_name",
    (
        ("SomeAuthor", "SomeAuthor"),
        ("Some-Author", "SomeAuthor"),
        ("Som3-Auth0r", "Som3Auth0r"),
        ("Som3_Auth0r", "Som3_Auth0r"),
        ("Some.Author", "SomeAuthor"),
        ("Some@Author", "SomeAuthor"),
        ("_someAuthor_", "someAuthor"),
        ("_someAuthor", "someAuthor"),
        ("someAuthor_", "someAuthor"),
        ("_", None),
        ("", None),
        ("!(¤#!¤)(!#=", None),
        ("_____", None),
    ),
)
def test_team_create_for_user(
    user: UserType, username: str, expected_name: Optional[str]
) -> None:
    user.username = username
    team = Team.get_or_create_for_user(user)
    if expected_name:
        assert team.name == expected_name
        assert team.members.count() == 1
        assert team.members.first().user == user
    else:
        assert team is None


@pytest.mark.django_db
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_create_for_user_name_taken(user: UserType, role: str) -> None:
    would_be_name = strip_unsupported_characters(user.username)
    team = Team.objects.create(name=would_be_name)
    if role:
        TeamMember.objects.create(
            team=team,
            user=user,
            role=TeamMemberRole.owner,
        )
    result = Team.get_or_create_for_user(user)
    if role:
        assert result == team
    else:
        assert result is None


@pytest.mark.django_db
@pytest.mark.parametrize("existing_team_role", TeamMemberRole.options() + [None])
def test_team_get_default_for_user(
    user: UserType, existing_team_role: Optional[str]
) -> None:
    existing_team = None
    if existing_team_role:
        existing_team = Team.objects.create(name="TestTeam")
        TeamMember.objects.create(
            team=existing_team,
            user=user,
            role=existing_team_role,
        )

    default_team = Team.get_default_for_user(user)

    if existing_team_role:
        assert default_team == existing_team
    else:
        assert bool(default_team)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type",
    [
        # Exclude service accounts as they have a team by default
        x
        for x in TestUserTypes.options()
        if x != TestUserTypes.service_account
    ],
)
def test_team_get_default_for_user_conflict(user_type: str):
    user = TestUserTypes.get_user_by_type(user_type)
    if user and user.is_authenticated:
        Team.objects.create(name=strip_unsupported_characters(user.username))
    default_team = Team.get_default_for_user(user)
    assert default_team is None


@pytest.mark.django_db
@pytest.mark.parametrize("role", TeamMemberRole.options())
def test_team_member_can_be_demoted(role: str) -> None:
    membership = TeamMemberFactory(role=role)
    result_map = {
        TeamMemberRole.owner: True,
        TeamMemberRole.member: False,
    }
    assert membership.can_be_demoted == result_map[role]


@pytest.mark.parametrize("role", TeamMemberRole.options())
@pytest.mark.django_db
def test_team_member_can_be_promoted(role) -> None:
    membership = TeamMemberFactory(role=role)
    result_map = {
        TeamMemberRole.owner: False,
        TeamMemberRole.member: True,
    }
    assert membership.can_be_promoted == result_map[role]


@pytest.mark.django_db
def test_team_member_manager_real_users(service_account, team_member) -> None:
    result = TeamMember.objects.real_users()
    assert team_member in result
    assert service_account.owner_membership not in result


@pytest.mark.django_db
def test_team_member_manager_service_accounts(service_account, team_member) -> None:
    result = TeamMember.objects.service_accounts()
    assert team_member not in result
    assert service_account.owner_membership in result


@pytest.mark.django_db
def test_team_member_manager_owners(service_account, team_member) -> None:
    service_account_member = service_account.owner_membership
    service_account_member.role = TeamMemberRole.owner
    service_account_member.save(update_fields=("role",))

    team_member.role = TeamMemberRole.owner
    team_member.save(update_fields=("role",))
    result = TeamMember.objects.owners()
    assert team_member in result
    assert service_account.owner_membership in result


@pytest.mark.django_db
def test_team_member_manager_real_user_owners(service_account, team_member) -> None:
    service_account_member = service_account.owner_membership
    service_account_member.role = TeamMemberRole.owner
    service_account_member.save(update_fields=("role",))

    team_member.role = TeamMemberRole.owner
    team_member.save(update_fields=("role",))
    result = TeamMember.objects.real_user_owners()
    assert team_member in result
    assert service_account.owner_membership not in result


@pytest.mark.django_db
def test_team_real_user_count(team) -> None:
    assert team.members.count() == 0
    assert team.members.real_users().count() == 0
    assert team.real_user_count == 0
    TeamMember.objects.create(user=UserFactory(), team=team)
    assert team.members.count() == 1
    assert team.members.real_users().count() == 1
    assert team.real_user_count == 1
    TeamMember.objects.create(user=ServiceAccountFactory().user, team=team)
    assert team.members.count() == 2
    assert team.members.real_users().count() == 1
    assert team.real_user_count == 1


@pytest.mark.django_db
def test_team_is_last_owner(team) -> None:
    member1 = TeamMemberFactory(
        team=team,
        role=TeamMemberRole.owner,
    )
    member2 = TeamMemberFactory(
        team=team,
        role=TeamMemberRole.member,
    )
    assert team.members.count() == 2
    assert team.members.owners().count() == 1
    assert team.is_last_owner(member1) is True
    assert team.is_last_owner(member2) is False
    assert team.is_last_owner(None) is False

    member2.role = TeamMemberRole.owner
    member2.save()

    assert team.members.owners().count() == 2
    assert team.is_last_owner(member1) is False
    assert team.is_last_owner(member2) is False

    member1.role = TeamMemberRole.member
    member1.save()

    assert team.members.owners().count() == 1
    assert team.is_last_owner(member1) is False
    assert team.is_last_owner(member2) is True


@pytest.mark.django_db
def test_team_validation_duplicates_ignore_case() -> None:
    TeamFactory.create(name="test")
    with pytest.raises(ValidationError) as e:
        TeamFactory.create(name="Test")
    assert "The author name already exists" in str(e.value)


@pytest.mark.parametrize("role", TeamMemberRole.options())
@pytest.mark.django_db
def test_team_add_member(team: Team, role: str) -> None:
    assert team.members.count() == 0
    membership = team.add_member(UserFactory(), role)
    assert membership.role == role
    assert team.members.count() == 1
    assert membership in team.members.all()


@pytest.mark.django_db
def test_team_member_str(team_member) -> None:
    assert team_member.user.username in str(team_member)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_ensure_user_can_manage_members(
    team: Team, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert team.can_user_manage_members(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_manage_members(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert team.can_user_manage_members(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_manage_members(user)
        assert "User has been deactivated" in str(e.value)
    else:
        if role is not None:
            TeamMember.objects.create(
                user=user,
                team=team,
                role=role,
            )
        if user_type == TestUserTypes.service_account:
            assert team.can_user_manage_members(user) is False
            with pytest.raises(ValidationError) as e:
                team.ensure_user_can_manage_members(user)
            assert "Service accounts are unable to manage members" in str(e.value)
        else:
            if role == TeamMemberRole.owner:
                assert team.can_user_manage_members(user) is True
                assert team.ensure_user_can_manage_members(user) is None
            else:
                assert team.can_user_manage_members(user) is False
                with pytest.raises(ValidationError) as e:
                    team.ensure_user_can_manage_members(user)
                assert "Must be an owner to manage team members" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_ensure_user_can_access(team: Team, user_type: str, role: str) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert team.can_user_access(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_access(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert team.can_user_access(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_access(user)
        assert "User has been deactivated" in str(e.value)
    else:
        if role is not None:
            TeamMember.objects.create(
                user=user,
                team=team,
                role=role,
            )
        if role is not None:
            assert team.can_user_access(user) is True
            assert team.ensure_user_can_access(user) is None
        else:
            assert team.can_user_access(user) is False
            with pytest.raises(ValidationError) as e:
                team.ensure_user_can_access(user)
            assert "Must be a member to access team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("team_active", (False, True))
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_ensure_can_upload_package(
    team: Team,
    team_active: bool,
    user_type: str,
    role: str,
) -> None:
    team.is_active = team_active
    team.save(update_fields=("is_active",))
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert team.can_user_upload(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_can_upload_package(user)
        assert "Must be authenticated" in str(e.value)
    else:
        if role is not None:
            TeamMember.objects.create(
                user=user,
                team=team,
                role=role,
            )
        if role is not None:
            if user_type == TestUserTypes.deactivated_user:
                assert team.can_user_upload(user) is False
                with pytest.raises(ValidationError) as e:
                    team.ensure_can_upload_package(user)
                assert "User has been deactivated" in str(e.value)
            else:
                if team_active:
                    assert team.can_user_upload(user) is True
                    assert team.ensure_user_can_access(user) is None
                else:
                    assert team.can_user_upload(user) is False
                    with pytest.raises(ValidationError) as e:
                        team.ensure_can_upload_package(user)
                    assert (
                        "The team has been deactivated and as such cannot receive new packages"
                        in str(e.value)
                    )
        else:
            assert team.can_user_upload(user) is False
            with pytest.raises(ValidationError) as e:
                team.ensure_can_upload_package(user)
            if user_type == TestUserTypes.deactivated_user:
                assert "User has been deactivated" in str(e.value)
            else:
                assert "Must be a member of team to upload package" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("role", TeamMemberRole.options())
def test_team_ensure_member_can_be_removed(team: Team, role: str) -> None:
    member = TeamMemberFactory(
        role=role,
        team=team,
    )
    if role == TeamMemberRole.owner:
        TeamMemberFactory(
            team=team,
            role=TeamMemberRole.owner,
        )
    assert team.can_member_be_removed(member) is True
    team.ensure_member_can_be_removed(member)


@pytest.mark.django_db
def test_team_ensure_member_can_be_removed_wrong_team(
    team: Team,
) -> None:
    member = TeamMemberFactory(role=TeamMemberRole.member)
    assert team.can_member_be_removed(member) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_can_be_removed(member)
    assert "Member is not a part of this team" in str(e.value)


@pytest.mark.django_db
def test_team_ensure_member_can_be_removed_no_member(
    team: Team,
) -> None:
    assert team.can_member_be_removed(None) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_can_be_removed(None)
    assert "Invalid member" in str(e.value)


@pytest.mark.django_db
def test_team_ensure_member_can_be_removed_last_owner(
    team: Team,
) -> None:
    owner = TeamMemberFactory(
        team=team,
        role=TeamMemberRole.owner,
    )
    assert team.members.count() == 1
    assert team.can_member_be_removed(owner) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_can_be_removed(owner)
    assert "Cannot remove last owner from team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("new_role", TeamMemberRole.options())
def test_team_ensure_member_role_can_be_changed_wrong_team(
    team: Team, new_role: str
) -> None:
    member = TeamMemberFactory(role=TeamMemberRole.member)
    assert team.can_member_role_be_changed(member, new_role) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_role_can_be_changed(member, new_role)
    assert "Member is not a part of this team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("new_role", TeamMemberRole.options())
def test_team_ensure_member_role_can_be_changed_no_member(
    team: Team, new_role: str
) -> None:
    assert team.can_member_role_be_changed(None, new_role) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_role_can_be_changed(None, new_role)
    assert "Invalid member" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("role", ("invalid", None))
def test_team_ensure_member_role_can_be_changed_invalid_role(
    team: Team, role: Optional[str]
) -> None:
    member = TeamMemberFactory(team=team, role=TeamMemberRole.member)
    assert team.can_member_role_be_changed(member, role) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_role_can_be_changed(member, role)
    assert "New role is invalid" in str(e.value)


@pytest.mark.django_db
def test_team_ensure_member_role_can_be_changed_last_owner(
    team: Team,
) -> None:
    new_role = TeamMemberRole.member
    member = TeamMemberFactory(team=team, role=TeamMemberRole.owner)
    assert team.can_member_role_be_changed(member, new_role) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_member_role_can_be_changed(member, new_role)
    assert "Cannot remove last owner from team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("old_role", TeamMemberRole.options())
@pytest.mark.parametrize("new_role", TeamMemberRole.options())
def test_team_ensure_member_role_can_be_changed(
    team: Team, old_role: str, new_role: str
) -> None:
    member = TeamMemberFactory(team=team, role=old_role)
    is_last_owner = (
        old_role == TeamMemberRole.owner and new_role == TeamMemberRole.member
    )
    if is_last_owner:
        TeamMemberFactory(team=team, role=TeamMemberRole.owner)
    assert team.can_member_role_be_changed(member, new_role) is True
    team.ensure_member_role_can_be_changed(member, new_role)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_ensure_user_can_disband(team: Team, user_type: str, role: str) -> None:
    user = TestUserTypes.get_user_by_type(user_type)

    if not user or not user.is_authenticated:
        assert team.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_disband(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert team.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_disband(user)
        assert "User has been deactivated" in str(e.value)
    elif user_type == TestUserTypes.service_account:
        assert team.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            team.ensure_user_can_disband(user)
        assert "Service accounts are unable to disband teams" in str(e.value)
    else:
        if role is not None:
            TeamMember.objects.create(
                user=user,
                team=team,
                role=role,
            )
        if role != TeamMemberRole.owner:
            assert team.can_user_disband(user) is False
            with pytest.raises(ValidationError) as e:
                team.ensure_user_can_disband(user)
            assert "Must be an owner to disband team" in str(e.value)
        else:
            assert team.can_user_disband(user) is True
            team.ensure_user_can_disband(user)


@pytest.mark.django_db
def test_team_ensure_user_can_disband_has_packages(
    team: Team, package: Package
) -> None:
    member = TeamMemberFactory(team=team, role=TeamMemberRole.owner)
    assert team.can_user_disband(member.user) is False
    with pytest.raises(ValidationError) as e:
        team.ensure_user_can_disband(member.user)
    assert "Unable to disband teams with packages" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "val_in, val_out",
    (
        ("as'\"df", "asdf"),
        ("_asdf", "asdf"),
        ("asdf_", "asdf"),
        ("_asdf_", "asdf"),
        ("as_df_", "as_df"),
        ("mr.test", "mrtest"),
        ("Mr.Test52", "MrTest52"),
        ("_Some._.name_", "Some_name"),
        ("_____Some._.name_____", "Some_name"),
        ("_____", ""),
        ("_a", "a"),
        ("", ""),
        (
            "_abcdefghij.klmnopqrst_uvwxyzAB#CDEFGHIJ_KLMNOPQRSTU_VXYZ0123-456789_",
            "abcdefghijklmnopqrst_uvwxyzABCDEFGHIJ_KLMNOPQRSTU_VXYZ0123456789",
        ),
    ),
)
def test_strip_unsupported_characters(val_in: str, val_out: str):
    assert strip_unsupported_characters(val_in) == val_out


@pytest.mark.django_db
def test_team_name_is_read_only(team: Team):
    team.name = team.name + "_test"
    with pytest.raises(ValidationError) as e:
        team.save()
    assert "Team name is read only" in str(e.value)


@pytest.mark.django_db
def test_team_settings_url(team: Team):
    assert bool(team.settings_url)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_ensure_can_create_service_account(
    team: Team, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        with pytest.raises(ValidationError) as e:
            team.ensure_can_create_service_account(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        with pytest.raises(ValidationError) as e:
            team.ensure_can_create_service_account(user)
        assert "User has been deactivated" in str(e.value)
    elif role is None:
        with pytest.raises(ValidationError) as e:
            team.ensure_can_create_service_account(user)
        assert "Must be a member to create a service account" in str(e.value)
    else:
        TeamMember.objects.create(
            user=user,
            team=team,
            role=role,
        )
        if role == TeamMemberRole.member:
            with pytest.raises(ValidationError) as e:
                team.ensure_can_create_service_account(user)
            assert "Must be an owner to create a service account" in str(e.value)
        if role == TeamMemberRole.owner:
            assert team.ensure_can_create_service_account(user) is None
