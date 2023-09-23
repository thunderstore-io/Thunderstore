import pytest
from django.forms import model_to_dict

from thunderstore.community.forms import PackageListingAdminForm, PackageListingForm
from thunderstore.community.models import Community, PackageCategory, PackageListing
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_package_listing_form_modify_categories_same_community(
    active_package_listing: PackageListing,
) -> None:
    category = PackageCategory.objects.create(
        community=active_package_listing.community,
        name="Test category",
        slug="test-category",
    )
    form = PackageListingForm(
        instance=active_package_listing,
        data={
            **(model_to_dict(active_package_listing)),
            **{
                "categories": [category.pk],
            },
        },
    )
    assert form.is_valid() is True
    listing = form.save()
    assert listing == active_package_listing
    assert category in listing.categories.all()


@pytest.mark.django_db
def test_package_listing_form_modify_categories_different_community(
    active_package_listing: PackageListing,
) -> None:
    category = PackageCategory.objects.create(
        community=Community.objects.create(name="Test"),
        name="Test category",
        slug="test-category",
    )
    form = PackageListingForm(
        instance=active_package_listing,
        data={
            **(model_to_dict(active_package_listing)),
            **{
                "categories": [category.pk],
            },
        },
    )
    assert form.is_valid() is False
    assert form.errors == {
        "categories": [
            "Select a valid choice. "
            f"{category.pk} "
            "is not one of the available choices."
        ]
    }


@pytest.mark.django_db
def test_package_listing_form_create_categories_same_community(
    community: Community,
    active_package: Package,
) -> None:
    category = PackageCategory.objects.create(
        community=community,
        name="Test category",
        slug="test-category",
    )
    form = PackageListingForm(
        data={
            "package": active_package.pk,
            "community": community.pk,
            "categories": [category.pk],
            "review_status": "unreviewed",
        }
    )
    assert form.is_valid() is True
    listing = form.save()
    assert category in listing.categories.all()


@pytest.mark.django_db
def test_package_listing_form_create_categories_different_community(
    community: Community,
    active_package: Package,
) -> None:
    category = PackageCategory.objects.create(
        community=Community.objects.create(name="Test"),
        name="Test category",
        slug="test-category",
    )
    form = PackageListingForm(
        data={
            "package": active_package.pk,
            "community": community.pk,
            "categories": [category.pk],
            "review_status": "unreviewed",
        }
    )
    expected_error = (
        "All PackageListing categories must match the community of the "
        "PackageListing"
    )
    assert form.is_valid() is False
    assert form.errors == {"__all__": [expected_error]}


@pytest.mark.django_db
def test_package_listing_form_admin_variant(active_package_listing: PackageListing):
    form1 = PackageListingAdminForm(instance=active_package_listing)
    assert form1.fields["categories"].queryset.query.is_empty() is False
    form2 = PackageListingAdminForm()
    assert form2.fields["categories"].queryset.query.is_empty() is True
