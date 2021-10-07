from typing import Optional

import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import (
    UploaderIdentityFactory,
    UploaderIdentityMemberFactory,
)
from thunderstore.repository.models import (
    Package,
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
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
def test_uploader_identity_can_user_upload(user, role, expected) -> None:
    identity = UploaderIdentityFactory.create()
    if role:
        UploaderIdentityMemberFactory.create(
            user=user,
            identity=identity,
            role=role,
        )
    assert identity.can_user_upload(user) == expected


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
def test_uploader_identity_create(name: str, should_fail: bool) -> None:
    if should_fail:
        with pytest.raises(ValidationError):
            UploaderIdentity.objects.create(name=name)
    else:
        identity = UploaderIdentity.objects.create(name=name)
        assert identity.name == name


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
def test_uploader_identity_create_for_user(
    user: UserType, username: str, expected_name: Optional[str]
) -> None:
    user.username = username
    identity = UploaderIdentity.get_or_create_for_user(user)
    if expected_name:
        assert identity.name == expected_name
        assert identity.members.count() == 1
        assert identity.members.first().user == user
    else:
        assert identity is None


@pytest.mark.django_db
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_create_for_user_name_taken(
    user: UserType, role: str
) -> None:
    would_be_name = strip_unsupported_characters(user.username)
    identity = UploaderIdentity.objects.create(name=would_be_name)
    if role:
        UploaderIdentityMember.objects.create(
            identity=identity,
            user=user,
            role=UploaderIdentityMemberRole.owner,
        )
    result = UploaderIdentity.get_or_create_for_user(user)
    if role:
        assert result == identity
    else:
        assert result is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "existing_team_role", UploaderIdentityMemberRole.options() + [None]
)
def test_uploader_identity_get_default_for_user(
    user: UserType, existing_team_role: Optional[str]
) -> None:
    existing_identity = None
    if existing_team_role:
        existing_identity = UploaderIdentity.objects.create(name="TestTeam")
        UploaderIdentityMember.objects.create(
            identity=existing_identity,
            user=user,
            role=existing_team_role,
        )

    default_identity = UploaderIdentity.get_default_for_user(user)

    if existing_team_role:
        assert default_identity == existing_identity
    else:
        assert bool(default_identity)


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
def test_uploader_identity_get_default_for_user_conflict(user_type: str):
    user = TestUserTypes.get_user_by_type(user_type)
    if user and user.is_authenticated:
        UploaderIdentity.objects.create(
            name=strip_unsupported_characters(user.username)
        )
    default_identity = UploaderIdentity.get_default_for_user(user)
    assert default_identity is None


@pytest.mark.django_db
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
def test_uploader_identity_member_can_be_demoted(role: str) -> None:
    membership = UploaderIdentityMemberFactory(role=role)
    result_map = {
        UploaderIdentityMemberRole.owner: True,
        UploaderIdentityMemberRole.member: False,
    }
    assert membership.can_be_demoted == result_map[role]


@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
@pytest.mark.django_db
def test_uploader_identity_member_can_be_promoted(role) -> None:
    membership = UploaderIdentityMemberFactory(role=role)
    result_map = {
        UploaderIdentityMemberRole.owner: False,
        UploaderIdentityMemberRole.member: True,
    }
    assert membership.can_be_promoted == result_map[role]


@pytest.mark.django_db
def test_uploader_identity_member_manager_real_users(
    service_account, uploader_identity_member
) -> None:
    result = UploaderIdentityMember.objects.real_users()
    assert uploader_identity_member in result
    assert service_account.owner_membership not in result


@pytest.mark.django_db
def test_uploader_identity_member_manager_service_accounts(
    service_account, uploader_identity_member
) -> None:
    result = UploaderIdentityMember.objects.service_accounts()
    assert uploader_identity_member not in result
    assert service_account.owner_membership in result


@pytest.mark.django_db
def test_uploader_identity_member_manager_owners(
    service_account, uploader_identity_member
) -> None:
    service_account_member = service_account.owner_membership
    service_account_member.role = UploaderIdentityMemberRole.owner
    service_account_member.save(update_fields=("role",))

    uploader_identity_member.role = UploaderIdentityMemberRole.owner
    uploader_identity_member.save(update_fields=("role",))
    result = UploaderIdentityMember.objects.owners()
    assert uploader_identity_member in result
    assert service_account.owner_membership in result


@pytest.mark.django_db
def test_uploader_identity_member_manager_real_user_owners(
    service_account, uploader_identity_member
) -> None:
    service_account_member = service_account.owner_membership
    service_account_member.role = UploaderIdentityMemberRole.owner
    service_account_member.save(update_fields=("role",))

    uploader_identity_member.role = UploaderIdentityMemberRole.owner
    uploader_identity_member.save(update_fields=("role",))
    result = UploaderIdentityMember.objects.real_user_owners()
    assert uploader_identity_member in result
    assert service_account.owner_membership not in result


@pytest.mark.django_db
def test_uploader_identity_member_count(uploader_identity) -> None:
    assert uploader_identity.members.count() == 0
    assert uploader_identity.member_count == 0
    UploaderIdentityMember.objects.create(
        user=UserFactory(), identity=uploader_identity
    )
    assert uploader_identity.members.count() == 1
    assert uploader_identity.member_count == 1


@pytest.mark.django_db
def test_uploader_identity_is_last_owner(uploader_identity) -> None:
    member1 = UploaderIdentityMemberFactory(
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    member2 = UploaderIdentityMemberFactory(
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.member,
    )
    assert uploader_identity.members.count() == 2
    assert uploader_identity.members.owners().count() == 1
    assert uploader_identity.is_last_owner(member1) is True
    assert uploader_identity.is_last_owner(member2) is False
    assert uploader_identity.is_last_owner(None) is False

    member2.role = UploaderIdentityMemberRole.owner
    member2.save()

    assert uploader_identity.members.owners().count() == 2
    assert uploader_identity.is_last_owner(member1) is False
    assert uploader_identity.is_last_owner(member2) is False

    member1.role = UploaderIdentityMemberRole.member
    member1.save()

    assert uploader_identity.members.owners().count() == 1
    assert uploader_identity.is_last_owner(member1) is False
    assert uploader_identity.is_last_owner(member2) is True


@pytest.mark.django_db
def test_uploader_identity_validation_duplicates_ignore_case() -> None:
    UploaderIdentityFactory.create(name="test")
    with pytest.raises(ValidationError) as e:
        UploaderIdentityFactory.create(name="Test")
    assert "The author name already exists" in str(e.value)


@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
@pytest.mark.django_db
def test_uploader_identity_add_member(
    uploader_identity: UploaderIdentity, role: str
) -> None:
    assert uploader_identity.members.count() == 0
    membership = uploader_identity.add_member(UserFactory(), role)
    assert membership.role == role
    assert uploader_identity.members.count() == 1
    assert membership in uploader_identity.members.all()


@pytest.mark.django_db
def test_uploader_identity_member_str(uploader_identity_member) -> None:
    assert uploader_identity_member.user.username in str(uploader_identity_member)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_user_can_manage_members(
    uploader_identity: UploaderIdentity, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert uploader_identity.can_user_manage_members(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_manage_members(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert uploader_identity.can_user_manage_members(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_manage_members(user)
        assert "User has been deactivated" in str(e.value)
    else:
        if role is not None:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=role,
            )
        if user_type == TestUserTypes.service_account:
            assert uploader_identity.can_user_manage_members(user) is False
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_user_can_manage_members(user)
            assert "Service accounts are unable to manage members" in str(e.value)
        else:
            if role == UploaderIdentityMemberRole.owner:
                assert uploader_identity.can_user_manage_members(user) is True
                assert uploader_identity.ensure_user_can_manage_members(user) is None
            else:
                assert uploader_identity.can_user_manage_members(user) is False
                with pytest.raises(ValidationError) as e:
                    uploader_identity.ensure_user_can_manage_members(user)
                assert "Must be an owner to manage team members" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_user_can_access(
    uploader_identity: UploaderIdentity, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert uploader_identity.can_user_access(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_access(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert uploader_identity.can_user_access(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_access(user)
        assert "User has been deactivated" in str(e.value)
    else:
        if role is not None:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=role,
            )
        if role is not None:
            assert uploader_identity.can_user_access(user) is True
            assert uploader_identity.ensure_user_can_access(user) is None
        else:
            assert uploader_identity.can_user_access(user) is False
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_user_can_access(user)
            assert "Must be a member to access team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("uploader_active", (False, True))
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_can_upload_package(
    uploader_identity: UploaderIdentity,
    uploader_active: bool,
    user_type: str,
    role: str,
) -> None:
    uploader_identity.is_active = uploader_active
    uploader_identity.save(update_fields=("is_active",))
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert uploader_identity.can_user_upload(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_can_upload_package(user)
        assert "Must be authenticated" in str(e.value)
    else:
        if role is not None:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=role,
            )
        if role is not None:
            if user_type == TestUserTypes.deactivated_user:
                assert uploader_identity.can_user_upload(user) is False
                with pytest.raises(ValidationError) as e:
                    uploader_identity.ensure_can_upload_package(user)
                assert "User has been deactivated" in str(e.value)
            else:
                if uploader_active:
                    assert uploader_identity.can_user_upload(user) is True
                    assert uploader_identity.ensure_user_can_access(user) is None
                else:
                    assert uploader_identity.can_user_upload(user) is False
                    with pytest.raises(ValidationError) as e:
                        uploader_identity.ensure_can_upload_package(user)
                    assert (
                        "The team has been deactivated and as such cannot receive new packages"
                        in str(e.value)
                    )
        else:
            assert uploader_identity.can_user_upload(user) is False
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_can_upload_package(user)
            if user_type == TestUserTypes.deactivated_user:
                assert "User has been deactivated" in str(e.value)
            else:
                assert "Must be a member of identity to upload package" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
def test_uploader_identity_ensure_member_can_be_removed(
    uploader_identity: UploaderIdentity, role: str
) -> None:
    member = UploaderIdentityMemberFactory(
        role=role,
        identity=uploader_identity,
    )
    if role == UploaderIdentityMemberRole.owner:
        UploaderIdentityMemberFactory(
            identity=uploader_identity,
            role=UploaderIdentityMemberRole.owner,
        )
    assert uploader_identity.can_member_be_removed(member) is True
    uploader_identity.ensure_member_can_be_removed(member)


@pytest.mark.django_db
def test_uploader_identity_ensure_member_can_be_removed_wrong_identity(
    uploader_identity: UploaderIdentity,
) -> None:
    member = UploaderIdentityMemberFactory(role=UploaderIdentityMemberRole.member)
    assert uploader_identity.can_member_be_removed(member) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_can_be_removed(member)
    assert "Member is not a part of this uploader identity" in str(e.value)


@pytest.mark.django_db
def test_uploader_identity_ensure_member_can_be_removed_no_member(
    uploader_identity: UploaderIdentity,
) -> None:
    assert uploader_identity.can_member_be_removed(None) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_can_be_removed(None)
    assert "Invalid member" in str(e.value)


@pytest.mark.django_db
def test_uploader_identity_ensure_member_can_be_removed_last_owner(
    uploader_identity: UploaderIdentity,
) -> None:
    owner = UploaderIdentityMemberFactory(
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    assert uploader_identity.members.count() == 1
    assert uploader_identity.can_member_be_removed(owner) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_can_be_removed(owner)
    assert "Cannot remove last owner from team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("new_role", UploaderIdentityMemberRole.options())
def test_uploader_identity_ensure_member_role_can_be_changed_wrong_identity(
    uploader_identity: UploaderIdentity, new_role: str
) -> None:
    member = UploaderIdentityMemberFactory(role=UploaderIdentityMemberRole.member)
    assert uploader_identity.can_member_role_be_changed(member, new_role) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_role_can_be_changed(member, new_role)
    assert "Member is not a part of this uploader identity" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("new_role", UploaderIdentityMemberRole.options())
def test_uploader_identity_ensure_member_role_can_be_changed_no_member(
    uploader_identity: UploaderIdentity, new_role: str
) -> None:
    assert uploader_identity.can_member_role_be_changed(None, new_role) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_role_can_be_changed(None, new_role)
    assert "Invalid member" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("role", ("invalid", None))
def test_uploader_identity_ensure_member_role_can_be_changed_invalid_role(
    uploader_identity: UploaderIdentity, role: Optional[str]
) -> None:
    member = UploaderIdentityMemberFactory(
        identity=uploader_identity, role=UploaderIdentityMemberRole.member
    )
    assert uploader_identity.can_member_role_be_changed(member, role) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_role_can_be_changed(member, role)
    assert "New role is invalid" in str(e.value)


@pytest.mark.django_db
def test_uploader_identity_ensure_member_role_can_be_changed_last_owner(
    uploader_identity: UploaderIdentity,
) -> None:
    new_role = UploaderIdentityMemberRole.member
    member = UploaderIdentityMemberFactory(
        identity=uploader_identity, role=UploaderIdentityMemberRole.owner
    )
    assert uploader_identity.can_member_role_be_changed(member, new_role) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_member_role_can_be_changed(member, new_role)
    assert "Cannot remove last owner from team" in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize("old_role", UploaderIdentityMemberRole.options())
@pytest.mark.parametrize("new_role", UploaderIdentityMemberRole.options())
def test_uploader_identity_ensure_member_role_can_be_changed(
    uploader_identity: UploaderIdentity, old_role: str, new_role: str
) -> None:
    member = UploaderIdentityMemberFactory(identity=uploader_identity, role=old_role)
    is_last_owner = (
        old_role == UploaderIdentityMemberRole.owner
        and new_role == UploaderIdentityMemberRole.member
    )
    if is_last_owner:
        UploaderIdentityMemberFactory(
            identity=uploader_identity, role=UploaderIdentityMemberRole.owner
        )
    assert uploader_identity.can_member_role_be_changed(member, new_role) is True
    uploader_identity.ensure_member_role_can_be_changed(member, new_role)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_user_can_disband(
    uploader_identity: UploaderIdentity, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)

    if not user or not user.is_authenticated:
        assert uploader_identity.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_disband(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        assert uploader_identity.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_disband(user)
        assert "User has been deactivated" in str(e.value)
    elif user_type == TestUserTypes.service_account:
        assert uploader_identity.can_user_disband(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_disband(user)
        assert "Service accounts are unable to disband teams" in str(e.value)
    else:
        if role is not None:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=role,
            )
        if role != UploaderIdentityMemberRole.owner:
            assert uploader_identity.can_user_disband(user) is False
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_user_can_disband(user)
            assert "Must be an owner to disband team" in str(e.value)
        else:
            assert uploader_identity.can_user_disband(user) is True
            uploader_identity.ensure_user_can_disband(user)


@pytest.mark.django_db
def test_uploader_identity_ensure_user_can_disband_has_packages(
    uploader_identity: UploaderIdentity, package: Package
) -> None:
    member = UploaderIdentityMemberFactory(
        identity=uploader_identity, role=UploaderIdentityMemberRole.owner
    )
    assert uploader_identity.can_user_disband(member.user) is False
    with pytest.raises(ValidationError) as e:
        uploader_identity.ensure_user_can_disband(member.user)
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
def test_uploader_identity_name_is_read_only(uploader_identity: UploaderIdentity):
    uploader_identity.name = uploader_identity.name + "_test"
    with pytest.raises(ValidationError) as e:
        uploader_identity.save()
    assert "UploaderIdentity name is read only" in str(e.value)


@pytest.mark.django_db
def test_uploader_identity_settings_url(uploader_identity: UploaderIdentity):
    assert bool(uploader_identity.settings_url)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_can_create_service_account(
    uploader_identity: UploaderIdentity, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_can_create_service_account(user)
        assert "Must be authenticated" in str(e.value)
    elif user_type == TestUserTypes.deactivated_user:
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_can_create_service_account(user)
        assert "User has been deactivated" in str(e.value)
    elif role is None:
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_can_create_service_account(user)
        assert "Must be a member to create a service account" in str(e.value)
    else:
        UploaderIdentityMember.objects.create(
            user=user,
            identity=uploader_identity,
            role=role,
        )
        if role == UploaderIdentityMemberRole.member:
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_can_create_service_account(user)
            assert "Must be an owner to create a service account" in str(e.value)
        if role == UploaderIdentityMemberRole.owner:
            assert uploader_identity.ensure_can_create_service_account(user) is None
