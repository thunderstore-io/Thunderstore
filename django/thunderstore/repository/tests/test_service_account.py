import pytest

from thunderstore.repository.models import (
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.service_account import CreateServiceAccountForm


@pytest.mark.django_db
def test_create_service_account(user, uploader_identity):
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
def test_create_service_account_not_member(user, uploader_identity):
    form = CreateServiceAccountForm(user, data={"identity": uploader_identity})
    assert form.is_valid() is False
    assert len(form.errors["identity"]) == 1
    assert (
        form.errors["identity"][0]
        == "Select a valid choice. That choice is not one of the available choices."
    )


@pytest.mark.django_db
def test_create_service_account_not_owner(user, uploader_identity):
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
