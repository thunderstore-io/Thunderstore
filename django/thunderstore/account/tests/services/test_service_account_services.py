import pytest

from conftest import TestUserTypes
from thunderstore.account.services import service_account as service_account_services
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import TeamMemberRole


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
            service_account_services.create_service_account(
                user, team, "TestServiceAccount"
            )
    else:
        service_account, token = service_account_services.create_service_account(
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
        service_account_services.create_service_account(
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
            service_account_services.delete_service_account(user, service_account)
    else:
        service_account_services.delete_service_account(user, service_account)
        assert service_account.pk is None


@pytest.mark.django_db
def test_delete_service_account_not_owner(service_account):
    user = UserFactory()
    service_account.owner.add_member(user=user, role=TeamMemberRole.member)
    error_msg = "Must be an owner to delete a service account"
    with pytest.raises(PermissionValidationError, match=error_msg):
        service_account_services.delete_service_account(user, service_account)
