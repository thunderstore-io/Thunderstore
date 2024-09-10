from typing import List

import pytest

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.community.models.package_category import PackageCategory
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.core.types import UserType
from thunderstore.repository.forms.package_listing import (
    PackageListingEditCategoriesForm,
)
from thunderstore.repository.models.team import TeamMember


@pytest.mark.django_db
def test_package_listing_edit_categories_form__correct_values__add_categories_to_empty__succeeds(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 0
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": package_categories},
    )
    assert form.is_valid() is True
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )
    returned_listing = form.save()
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 3
    )
    after_action_db_state = PackageListing.objects.get(
        pk=active_package_listing.pk
    ).categories.all()
    assert len(after_action_db_state) == 3
    assert (
        len(
            set(returned_listing.categories.all()).symmetric_difference(
                after_action_db_state
            )
        )
        == 0
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_form__correct_values__remove_one_category__succeeds(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": package_categories[:2]},
    )
    assert form.is_valid() is True
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )
    returned_listing = form.save()
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 1
    )
    after_action_db_state = PackageListing.objects.get(
        pk=active_package_listing.pk
    ).categories.all()
    assert len(after_action_db_state) == 2
    assert (
        len(
            set(returned_listing.categories.all()).symmetric_difference(
                after_action_db_state
            )
        )
        == 0
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_form__correct_values__remove_all_categories__succeeds(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": []},
    )
    assert form.is_valid() is True
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )
    returned_listing = form.save()
    after_action_db_state = PackageListing.objects.get(
        pk=active_package_listing.pk
    ).categories.all()
    assert len(after_action_db_state) == 0
    assert len(set(apl_categories).symmetric_difference(after_action_db_state)) == 3
    assert (
        len(
            set(returned_listing.categories.all()).symmetric_difference(
                after_action_db_state
            )
        )
        == 0
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_form__bad_initial_value__fails(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": {"bad": "bad"}},
        data={"categories": package_categories},
    )
    assert form.is_valid() is False
    assert "Listings current categories do not match provided ones" in str(
        repr(form.errors)
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_form__bad_data_value__fails(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": {"bad": "bad"}},
    )
    assert form.is_valid() is False
    assert "“bad” is not a valid value." in str(repr(form.errors))


@pytest.mark.django_db
def test_package_listing_edit_categories_form__user_is_not_in_team__fails(
    user: UserType,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    assert (
        len(
            TeamMember.objects.filter(
                team=active_package_listing.package.namespace.team, user=user
            )
        )
        == 0
    )
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": package_categories},
    )
    assert form.is_valid() is False
    assert "Must have listing management permission" in str(repr(form.errors))


@pytest.mark.django_db
def test_package_listing_edit_categories_form__user_is_deactivated__fails(
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    team_member.user.is_active = False
    team_member.user.save()
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=team_member.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": package_categories},
    )
    assert form.is_valid() is False
    assert "User has been deactivated" in str(repr(form.errors))


@pytest.mark.django_db
def test_package_listing_edit_categories_form__user_is_service_account__fails(
    service_account: ServiceAccount,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3
    form = PackageListingEditCategoriesForm(
        user=service_account.user,
        instance=active_package_listing,
        initial={"categories": apl_categories},
        data={"categories": package_categories},
    )
    assert form.is_valid() is False
    assert "Service accounts are unable to perform this action" in str(
        repr(form.errors)
    )
