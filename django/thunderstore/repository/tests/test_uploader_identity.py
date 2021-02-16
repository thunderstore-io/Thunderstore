import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import (
    UploaderIdentityFactory,
    UploaderIdentityMemberFactory,
)
from thunderstore.repository.models import (
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
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
def test_uploader_identity_can_user_upload(user, role, expected):
    identity = UploaderIdentityFactory.create()
    if role:
        UploaderIdentityMemberFactory.create(
            user=user,
            identity=identity,
            role=role,
        )
    assert identity.can_user_upload(user) == expected


@pytest.mark.parametrize(
    "author_name, should_fail",
    (
        ("SomeAuthor", False),
        ("Some-Author", False),
        ("Som3-Auth0r", False),
        ("Som3_Auth0r", False),
        ("Some.Author", False),
        ("Some@Author", True),
    ),
)
@pytest.mark.django_db
def test_uploader_identity_creation(user, author_name, should_fail):
    user.username = author_name
    if should_fail:
        with pytest.raises(ValidationError):
            UploaderIdentity.get_or_create_for_user(user)
    else:
        identity = UploaderIdentity.get_or_create_for_user(user)
        assert identity.name == author_name


@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
@pytest.mark.django_db
def test_uploader_identity_member_can_be_demoted(role):
    membership = UploaderIdentityMemberFactory(role=role)
    result_map = {
        UploaderIdentityMemberRole.owner: True,
        UploaderIdentityMemberRole.member: False,
    }
    assert membership.can_be_demoted == result_map[role]


@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
@pytest.mark.django_db
def test_uploader_identity_member_can_be_promoted(role):
    membership = UploaderIdentityMemberFactory(role=role)
    result_map = {
        UploaderIdentityMemberRole.owner: False,
        UploaderIdentityMemberRole.member: True,
    }
    assert membership.can_be_promoted == result_map[role]


@pytest.mark.django_db
def test_uploader_identity_member_manager_real_users(
    service_account, uploader_identity_member
):
    result = UploaderIdentityMember.objects.real_users()
    assert uploader_identity_member in result
    assert service_account.owner_membership not in result


@pytest.mark.django_db
def test_uploader_identity_member_manager_service_accounts(
    service_account, uploader_identity_member
):
    result = UploaderIdentityMember.objects.service_accounts()
    assert uploader_identity_member not in result
    assert service_account.owner_membership in result


@pytest.mark.django_db
def test_uploader_identity_member_count(uploader_identity):
    assert uploader_identity.members.count() == 0
    assert uploader_identity.member_count == 0
    UploaderIdentityMember.objects.create(
        user=UserFactory(), identity=uploader_identity
    )
    assert uploader_identity.members.count() == 1
    assert uploader_identity.member_count == 1


@pytest.mark.django_db
def test_uploader_identity_validation_duplicates_ignore_case():
    UploaderIdentityFactory.create(name="test")
    with pytest.raises(ValidationError) as e:
        UploaderIdentityFactory.create(name="Test")
    assert "The author name already exists" in str(e.value)


@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options())
@pytest.mark.django_db
def test_uploader_identity_add_member(uploader_identity: UploaderIdentity, role: str):
    assert uploader_identity.members.count() == 0
    membership = uploader_identity.add_member(UserFactory(), role)
    assert membership.role == role
    assert uploader_identity.members.count() == 1
    assert membership in uploader_identity.members.all()


@pytest.mark.django_db
def test_uploader_identity_member_str(uploader_identity_member):
    assert uploader_identity_member.user.username in str(uploader_identity_member)


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_user_can_manage_members(
    uploader_identity: UploaderIdentity, user_type: str, role: str
):
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert uploader_identity.can_user_manage_members(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_manage_members(user)
        assert "Must be authenticated" in str(e.value)
    else:
        if role is not None:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=role,
            )
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
):
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type in TestUserTypes.fake_users():
        assert uploader_identity.can_user_access(user) is False
        with pytest.raises(ValidationError) as e:
            uploader_identity.ensure_user_can_access(user)
        assert "Must be authenticated" in str(e.value)
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
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", UploaderIdentityMemberRole.options() + [None])
def test_uploader_identity_ensure_can_upload_package(
    uploader_identity: UploaderIdentity, user_type: str, role: str
):
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
            assert uploader_identity.can_user_upload(user) is True
            assert uploader_identity.ensure_user_can_access(user) is None
        else:
            assert uploader_identity.can_user_upload(user) is False
            with pytest.raises(ValidationError) as e:
                uploader_identity.ensure_can_upload_package(user)
            assert "Must be a member of identity to upload package" in str(e.value)
