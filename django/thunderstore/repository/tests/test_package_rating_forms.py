import pytest
from rest_framework.exceptions import PermissionDenied

from thunderstore.core.types import UserType
from thunderstore.repository.forms.package_rating import RateForm
from thunderstore.repository.models import Package
from thunderstore.repository.models.package_rating import PackageRating


@pytest.mark.django_db
def test_package_rating_form__correct_values__succeeds(
    user: UserType, package: Package
) -> None:
    # Rated
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "rated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 1
    assert result_state == "rated"
    assert score == 1
    # Unrated
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "unrated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert result_state == "unrated"
    assert score == 0


@pytest.mark.django_db
def test_package_rating_form__already_on_state__succeeds(
    user: UserType, package: Package
) -> None:
    # Rated
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "rated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 1
    assert result_state == "rated"
    assert score == 1
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "rated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 1
    assert result_state == "rated"
    assert score == 1
    # Unrated
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "unrated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert result_state == "unrated"
    assert score == 0
    # Second time
    p = Package.objects.get(pk=package.pk)
    form = RateForm(
        user=user,
        package=p,
        data={"target_state": "unrated"},
    )
    assert form.is_valid() is True
    (result_state, score) = form.execute()
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert result_state == "unrated"
    assert score == 0


@pytest.mark.django_db
def test_package_rating_form__bad_target_state__fails(
    user: UserType, package: Package
) -> None:
    error = "Given target_state is invalid"
    form = RateForm(
        user=user,
        package=package,
        data={"target_state": "bad"},
    )
    assert form.is_valid() is False
    assert error in str(repr(form.errors))


@pytest.mark.django_db
def test_package_rating_form__user_none__fails(
    package: Package,
) -> None:
    form = RateForm(
        user=None,
        package=package,
        data={"target_state": "rated"},
    )
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "Must be authenticated" in str(e.value)


@pytest.mark.django_db
def test_package_rating_form__user_deactivated__fails(
    user: UserType, package: Package
) -> None:
    user.is_active = False
    user.save()
    form = RateForm(
        user=user,
        package=package,
        data={"target_state": "rated"},
    )
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "User has been deactivated" in str(e.value)


@pytest.mark.django_db
def test_package_rating_form__user_is_service_account__fails(
    service_account: UserType, package: Package
) -> None:
    form = RateForm(
        user=service_account.user,
        package=package,
        data={"target_state": "rated"},
    )
    with pytest.raises(PermissionDenied) as e:
        form.is_valid()
    assert "Service accounts are unable to perform this action" in str(e.value)
