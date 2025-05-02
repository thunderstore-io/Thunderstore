import pytest
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.services.package import (
    deprecate_package,
    rate_package,
    undeprecate_package,
)
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.repository.models import TeamMember, TeamMemberRole


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_deprecate",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, False),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_deprecate_package_user_roles(active_package, user_role, can_deprecate):
    active_package.is_deprecated = False
    active_package.save()
    agent = TestUserTypes.get_user_by_type(user_role)
    if not can_deprecate:
        with pytest.raises(PermissionValidationError):
            deprecate_package(agent, active_package)
    else:
        deprecate_package(agent, active_package)
        active_package.refresh_from_db()
        assert active_package.is_deprecated is True


@pytest.mark.django_db
def test_deprecate_package_not_team_member(package, user):
    error_msg = "Must be a member of team to manage package"
    with pytest.raises(PermissionValidationError, match=error_msg):
        deprecate_package(user, package)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_undeprecate",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, False),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_undeprecate_package_user_roles(active_package, user_role, can_undeprecate):
    active_package.is_deprecated = True
    active_package.save()
    agent = TestUserTypes.get_user_by_type(user_role)
    if not can_undeprecate:
        with pytest.raises(PermissionValidationError):
            undeprecate_package(agent, active_package)
    else:
        undeprecate_package(agent, active_package)
        active_package.refresh_from_db()
        assert active_package.is_deprecated is False


@pytest.mark.django_db
def test_undeprecate_package(package, user):
    TeamMember.objects.create(
        user=user,
        team=package.owner,
        role=TeamMemberRole.owner,
    )

    package.is_deprecated = True
    package.save()

    assert package.is_deprecated is True
    package = undeprecate_package(user, package)
    assert package.is_deprecated is False


@pytest.mark.django_db
def test_undeprecate_package_not_team_member(package, user):
    error_msg = "Must be a member of team to manage package"
    with pytest.raises(PermissionValidationError, match=error_msg):
        undeprecate_package(user, package)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_role, can_rate",
    [
        (TestUserTypes.no_user, False),
        (TestUserTypes.unauthenticated, False),
        (TestUserTypes.regular_user, True),
        (TestUserTypes.deactivated_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_rate_package_user_roles(active_package, user_role, can_rate):
    agent = TestUserTypes.get_user_by_type(user_role)
    if not can_rate:
        with pytest.raises(PermissionDenied):
            rate_package(agent, active_package, "rated")
    else:
        rating_score, result_state = rate_package(agent, active_package, "rated")
        assert rating_score == 1
        assert result_state == "rated"


@pytest.mark.django_db
def test_rate_package_invalid_target_state(active_package, user):
    error_msg = "Invalid target_state"
    with pytest.raises(ValidationError, match=error_msg):
        rate_package(user, active_package, "invalid_state")
