import pytest

from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import (
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.service_account import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
)


@pytest.mark.django_db
def test_service_account_fixture(service_account):
    assert service_account.uuid.hex == service_account.user.username


@pytest.mark.django_db
def test_service_account_create(user, uploader_identity):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    form = CreateServiceAccountForm(user, data={"identity": uploader_identity})
    assert form.is_valid()
    service_account = form.save()
    assert service_account.uuid.hex == service_account.user.username


@pytest.mark.django_db
def test_service_account_create_not_member(user, uploader_identity):
    assert uploader_identity.members.filter(user=user).exists() is False
    form = CreateServiceAccountForm(user, data={"identity": uploader_identity})
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
    form = CreateServiceAccountForm(user, data={"identity": uploader_identity})
    assert form.is_valid() is False
    assert len(form.errors["identity"]) == 1
    assert (
        form.errors["identity"][0]
        == "Must be identity owner to create a service account"
    )


@pytest.mark.django_db
def test_service_account_delete(service_account):
    member = service_account.owner.members.first()
    assert member.role == UploaderIdentityMemberRole.owner
    form = DeleteServiceAccountForm(
        member.user,
        data={"service_account": service_account},
    )
    assert form.is_valid()
    form.save()


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
