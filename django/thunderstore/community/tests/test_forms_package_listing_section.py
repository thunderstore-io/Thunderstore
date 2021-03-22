import pytest
from django.forms import model_to_dict

from thunderstore.community.forms import PackageListingSectionForm
from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)


@pytest.mark.django_db
@pytest.mark.parametrize("category_set", ("require_categories", "exclude_categories"))
def test_package_listing_section_form_modify_categories_same_community(
    package_listing_section: PackageListingSection,
    category_set: str,
) -> None:
    category = PackageCategory.objects.create(
        community=package_listing_section.community,
        name="Test category",
        slug="test-category",
    )
    form = PackageListingSectionForm(
        instance=package_listing_section,
        data={
            **(model_to_dict(package_listing_section)),
            **{
                category_set: [category.pk],
            },
        },
    )
    is_valid = form.is_valid()
    print(str(repr(form.errors)))
    assert is_valid is True
    listing = form.save()
    assert listing == package_listing_section
    assert category in getattr(listing, category_set).all()


@pytest.mark.django_db
@pytest.mark.parametrize("category_set", ("require_categories", "exclude_categories"))
def test_package_listing_section_form_modify_categories_different_community(
    package_listing_section: PackageListingSection,
    category_set: str,
) -> None:
    category = PackageCategory.objects.create(
        community=Community.objects.create(name="Test"),
        name="Test category",
        slug="test-category",
    )
    form = PackageListingSectionForm(
        instance=package_listing_section,
        data={
            **(model_to_dict(package_listing_section)),
            **{
                category_set: [category.pk],
            },
        },
    )
    assert form.is_valid() is False
    assert form.errors == {
        category_set: [
            "Select a valid choice. "
            f"{category.pk} "
            "is not one of the available choices."
        ]
    }


@pytest.mark.django_db
@pytest.mark.parametrize("category_set", ("require_categories", "exclude_categories"))
def test_package_listing_section_form_create_categories_same_community(
    community: Community,
    category_set: str,
) -> None:
    category = PackageCategory.objects.create(
        community=community,
        name="Test category",
        slug="test-category",
    )
    form = PackageListingSectionForm(
        data={
            "name": "Test Section",
            "slug": "test-section",
            "priority": 0,
            "community": community.pk,
            category_set: [category.pk],
        }
    )
    is_valid = form.is_valid()
    print(str(repr(form.errors)))
    assert is_valid is True
    listing = form.save()
    assert category in getattr(listing, category_set).all()


@pytest.mark.django_db
@pytest.mark.parametrize("category_set", ("require_categories", "exclude_categories"))
def test_package_listing_section_form_create_categories_different_community(
    community: Community,
    category_set: str,
) -> None:
    category = PackageCategory.objects.create(
        community=Community.objects.create(name="Test"),
        name="Test category",
        slug="test-category",
    )
    form = PackageListingSectionForm(
        data={
            "name": "Test Section",
            "slug": "test-section",
            "priority": 0,
            "community": community.pk,
            category_set: [category.pk],
        }
    )
    expected_error = "All categories must match the selected community"
    assert form.is_valid() is False
    assert form.errors == {"__all__": [expected_error]}
