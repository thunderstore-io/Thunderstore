import pytest
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token

from thunderstore.account.forms import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
    EditServiceAccountForm,
)
from thunderstore.account.models import ServiceAccount
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import TeamMember, TeamMemberRole


@pytest.mark.django_db
def test_service_account_fixture(service_account):
    username = ServiceAccount.create_username(service_account.uuid.hex)
    assert username == service_account.user.username


@pytest.mark.django_db
def test_service_account_create(user, team):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "Nickname"},
    )
    assert form.is_valid() is True
    service_account = form.save()
    username = ServiceAccount.create_username(service_account.uuid.hex)
    assert username == service_account.user.username
    assert service_account.user.first_name == "Nickname"
    assert service_account.api_token is not None
    assert service_account.api_token.startswith("pbkdf2_sha256$524288$w520TEzFVlsO$")
    assert service_account.created_at is not None
    assert service_account.last_used is None
    assert (
        team.members.filter(
            user=service_account.user,
            role=TeamMemberRole.member,
        ).exists()
        is True
    )


@pytest.mark.django_db
def test_service_account_create_error_on_save(user, team):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "x" * 1000},
    )

    assert form.is_valid() is False
    with pytest.raises(ValueError):
        form.save()


@pytest.mark.django_db
def test_service_account_create_nickname_too_long(user, team):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "x" * 1000},
    )
    assert form.is_valid() is False
    assert len(form.errors["nickname"]) == 1
    assert (
        form.errors["nickname"][0]
        == "Ensure this value has at most 32 characters (it has 1000)."
    )


@pytest.mark.django_db
def test_service_account_create_not_member(user, team):
    assert team.members.filter(user=user).exists() is False
    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "Nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["team"]) == 1
    assert (
        form.errors["team"][0]
        == "Select a valid choice. That choice is not one of the available choices."
    )


@pytest.mark.django_db
def test_service_account_create_not_owner(user, team):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.member,
    )
    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "Nickname"},
    )
    with pytest.raises(ValidationError):
        form.save()
    assert form.is_valid() is False
    assert len(form.errors["__all__"]) == 1
    assert form.errors["__all__"][0] == "Must be an owner to create a service account"


@pytest.mark.django_db
def test_service_account_delete(django_user_model, service_account):
    member = service_account.owner.members.first()
    assert member.role == TeamMemberRole.owner
    assert django_user_model.objects.filter(pk=service_account.user.pk).exists() is True
    form = DeleteServiceAccountForm(
        member.user,
        data={"service_account": service_account},
    )
    assert form.is_valid()
    form.save()
    assert ServiceAccount.objects.filter(pk=service_account.pk).exists() is False
    assert (
        django_user_model.objects.filter(pk=service_account.user.pk).exists() is False
    )


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
def test_service_account_delete_error_on_save(service_account):
    user = UserFactory.create()

    form = DeleteServiceAccountForm(
        user,
        data={"service_account": service_account},
    )

    assert form.is_valid() is False
    with pytest.raises(ValueError):
        form.save()


@pytest.mark.django_db
def test_service_account_delete_not_owner(service_account):
    user = UserFactory.create()
    TeamMember.objects.create(
        user=user,
        team=service_account.owner,
        role=TeamMemberRole.member,
    )
    form = DeleteServiceAccountForm(
        user,
        data={"service_account": service_account},
    )
    with pytest.raises(ValidationError):
        form.save()
    assert form.is_valid() is False
    assert len(form.errors["__all__"]) == 1
    assert form.errors["__all__"][0] == "Must be an owner to delete a service account"


@pytest.mark.django_db
def test_service_account_edit_nickname(service_account):
    member = service_account.owner.members.first()
    assert member.role == TeamMemberRole.owner
    form = EditServiceAccountForm(
        member.user,
        data={"service_account": service_account, "nickname": "New nickname"},
    )
    assert form.is_valid()

    service_account = form.save()
    assert service_account.user.first_name == "New nickname"
    assert service_account.nickname == "New nickname"

    service_account = ServiceAccount.objects.get(pk=service_account.pk)
    assert service_account.user.first_name == "New nickname"
    assert service_account.nickname == "New nickname"


@pytest.mark.django_db
def test_service_account_edit_nickname_too_long(service_account):
    member = service_account.owner.members.first()
    assert member.role == TeamMemberRole.owner
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
    TeamMember.objects.create(
        user=user,
        team=service_account.owner,
        role=TeamMemberRole.member,
    )
    form = EditServiceAccountForm(
        user,
        data={"service_account": service_account, "nickname": "New nickname"},
    )
    assert form.is_valid() is False
    assert len(form.errors["service_account"]) == 1
    assert (
        form.errors["service_account"][0]
        == "Must be an owner to edit a service account"
    )
