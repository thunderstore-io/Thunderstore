import pytest

from thunderstore.account.forms import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
    EditServiceAccountForm,
    create_service_account_username,
)
from thunderstore.account.models import ServiceAccount
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import (
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)


@pytest.mark.django_db
def test_service_account_fixture(service_account):
    username = create_service_account_username(service_account.uuid.hex)
    assert username == service_account.user.username


@pytest.mark.django_db
def test_service_account_create(user, uploader_identity):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"identity": uploader_identity, "nickname": "Nickname"},
    )
    assert form.is_valid()
    service_account = form.save()
    username = create_service_account_username(service_account.uuid.hex)
    assert username == service_account.user.username
    assert service_account.user.first_name == "Nickname"


@pytest.mark.django_db
def test_service_account_create_nickname_too_long(user, uploader_identity):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"identity": uploader_identity, "nickname": "x" * 1000},
    )
    assert form.is_valid() is False
    assert len(form.errors["nickname"]) == 1
    assert (
        form.errors["nickname"][0]
        == "Ensure this value has at most 32 characters (it has 1000)."
    )


@pytest.mark.django_db
def test_service_account_create_not_member(user, uploader_identity):
    assert uploader_identity.members.filter(user=user).exists() is False
    form = CreateServiceAccountForm(
        user,
        data={"identity": uploader_identity, "nickname": "Nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["identity"]) == 1
    assert (
        form.errors["identity"][0]
        == "Select a valid choice. That choice is not one of the available choices."
    )


@pytest.mark.django_db
def test_service_account_create_not_owner(user, uploader_identity):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.member,
    )
    form = CreateServiceAccountForm(
        user,
        data={"identity": uploader_identity, "nickname": "Nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["identity"]) == 1
    assert (
        form.errors["identity"][0]
        == "Must be identity owner to create a service account"
    )


@pytest.mark.django_db
def test_service_account_delete(django_user_model, service_account):
    User = django_user_model
    member = service_account.owner.members.first()
    assert member.role == UploaderIdentityMemberRole.owner
    assert User.objects.filter(pk=service_account.user.pk).exists() is True
    form = DeleteServiceAccountForm(
        member.user,
        data={"service_account": service_account},
    )
    assert form.is_valid()
    form.save()
    assert ServiceAccount.objects.filter(pk=service_account.pk).exists() is False
    assert User.objects.filter(pk=service_account.user.pk).exists() is False


@pytest.mark.django_db
def test_service_account_delete_not_member(service_account):
    user = UserFactory.create()
    assert service_account.owner.members.filter(user=user).exists() is False
    form = DeleteServiceAccountForm(
        user,
        data={"service_account": service_account},
    )
    assert form.is_valid() is False
    assert len(form.errors["service_account"]) == 1
    assert (
        form.errors["service_account"][0]
        == "Select a valid choice. That choice is not one of the available choices."
    )


@pytest.mark.django_db
def test_service_account_delete_not_owner(service_account):
    user = UserFactory.create()
    UploaderIdentityMember.objects.create(
        user=user,
        identity=service_account.owner,
        role=UploaderIdentityMemberRole.member,
    )
    form = DeleteServiceAccountForm(
        user,
        data={"service_account": service_account},
    )
    assert form.is_valid() is False
    assert len(form.errors["service_account"]) == 1
    assert (
        form.errors["service_account"][0]
        == "Must be identity owner to delete a service account"
    )


@pytest.mark.django_db
def test_service_account_edit_nickname(service_account):
    member = service_account.owner.members.first()
    assert member.role == UploaderIdentityMemberRole.owner
    form = EditServiceAccountForm(
        member.user,
        data={"service_account": service_account, "nickname": "New nickname"},
    )
    assert form.is_valid()
    service_account = form.save()
    assert service_account.user.first_name == "New nickname"
    assert service_account.nickname == "New nickname"


@pytest.mark.django_db
def test_service_account_edit_nickname_too_long(service_account):
    member = service_account.owner.members.first()
    assert member.role == UploaderIdentityMemberRole.owner
    form = EditServiceAccountForm(
        member.user,
        data={"service_account": service_account, "nickname": "x" * 1000},
    )
    assert form.is_valid() is False
    assert len(form.errors["nickname"]) == 1
    assert (
        form.errors["nickname"][0]
        == "Ensure this value has at most 32 characters (it has 1000)."
    )


@pytest.mark.django_db
def test_service_account_edit_not_member(service_account):
    user = UserFactory.create()
    assert service_account.owner.members.filter(user=user).exists() is False
    form = EditServiceAccountForm(
        user,
        data={"service_account": service_account, "nickname": "New nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["service_account"]) == 1
    assert (
        form.errors["service_account"][0]
        == "Select a valid choice. That choice is not one of the available choices."
    )


@pytest.mark.django_db
def test_service_account_edit_not_owner(service_account):
    user = UserFactory.create()
    UploaderIdentityMember.objects.create(
        user=user,
        identity=service_account.owner,
        role=UploaderIdentityMemberRole.member,
    )
    form = EditServiceAccountForm(
        user,
        data={"service_account": service_account, "nickname": "New nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["service_account"]) == 1
    assert (
        form.errors["service_account"][0]
        == "Must be identity owner to edit a service account"
    )
