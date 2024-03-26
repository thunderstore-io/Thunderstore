import pytest
from django.forms import ValidationError

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.repository.forms import DeprecateForm
from thunderstore.repository.models import Package
from thunderstore.repository.models.team import TeamMember


@pytest.mark.django_db
def test_package_deprecate_form__correct_values__succeeds(
    team_member: TeamMember, package: Package
) -> None:
    # Deprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Undeprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False


@pytest.mark.django_db
def test_package_deprecate_form__already_on_state__succeeds(
    team_member: TeamMember, package: Package
) -> None:
    # Deprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Undeprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=team_member.user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False


@pytest.mark.django_db
def test_package_deprecate_form__bad_value__fails(
    team_member: TeamMember, package: Package
) -> None:
    error = "Given value for is_deprecated is invalid."
    form = DeprecateForm(
        user=team_member.user,
        instance=package,
        data={"is_deprecated": "bad"},
    )
    assert form.is_valid() is False
    assert error in str(repr(form.errors))


@pytest.mark.django_db
def test_package_deprecate_form__user_none__fails(
    package: Package,
) -> None:
    form = DeprecateForm(
        user=None,
        instance=package,
        data={"is_deprecated": True},
    )
    with pytest.raises(ValidationError) as e:
        form.clean()
    assert "Must be authenticated" in str(e.value)


@pytest.mark.django_db
def test_package_deprecate_form__user_deactivated__fails(
    team_member: TeamMember, package: Package
) -> None:
    team_member.user.is_active = False
    team_member.user.save()
    form = DeprecateForm(
        user=team_member.user,
        instance=package,
        data={"is_deprecated": True},
    )
    with pytest.raises(ValidationError) as e:
        form.clean()
    assert "User has been deactivated" in str(e.value)


@pytest.mark.django_db
def test_package_deprecate_form__user_is_service_account__fails(
    service_account: ServiceAccount, package: Package
) -> None:
    form = DeprecateForm(
        user=service_account.user,
        instance=package,
        data={"is_deprecated": True},
    )
    with pytest.raises(ValidationError) as e:
        form.clean()
    assert "Service accounts are unable to perform this action" in str(e.value)
