import pytest
from rest_framework.exceptions import PermissionDenied

from thunderstore.core.types import UserType
from thunderstore.repository.forms import DeprecateForm
from thunderstore.repository.models import Package
from thunderstore.repository.models.package_rating import PackageRating


@pytest.mark.django_db
def test_package_deprecate_form__correct_values__succeeds(
    user: UserType, package: Package
) -> None:
    # Deprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Undeprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False


@pytest.mark.django_db
def test_package_deprecate_form__already_on_state__succeeds(
    user: UserType, package: Package
) -> None:
    # Deprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": True},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == True
    # Undeprecate
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = DeprecateForm(
        user=user,
        instance=p,
        data={"is_deprecated": False},
    )
    assert form.is_valid() is True
    pkg = form.execute()
    assert pkg.is_deprecated == False


@pytest.mark.django_db
def test_package_deprecate_form__bad_is_deprecated__fails(
    user: UserType, package: Package
) -> None:
    error = "Given is_deprecated is invalid"
    form = DeprecateForm(
        user=user,
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
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "Must be authenticated" in str(e.value)


@pytest.mark.django_db
def test_package_deprecate_form__user_deactivated__fails(
    user: UserType, package: Package
) -> None:
    user.is_active = False
    user.save()
    form = DeprecateForm(
        user=user,
        instance=package,
        data={"is_deprecated": True},
    )
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "User has been deactivated" in str(e.value)


@pytest.mark.django_db
def test_package_deprecate_form__user_is_service_account__fails(
    service_account: UserType, package: Package
) -> None:
    form = DeprecateForm(
        user=service_account.user,
        instance=package,
        data={"is_deprecated": True},
    )
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "Service accounts are unable to perform this action" in str(e.value)
