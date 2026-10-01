import pytest

from thunderstore.community.factories import (
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.core.management.commands.content.base import ContentPopulatorContext
from thunderstore.core.management.commands.content.package_listing import (
    ListingPopulator,
    desired_listing_categories,
    desired_nsfw,
)
from thunderstore.repository.factories import PackageFactory


@pytest.mark.django_db
def test_listing_populator_assigns_stable_categories_and_nsfw() -> None:
    community = CommunityFactory()
    package = PackageFactory()
    mods = PackageCategoryFactory(community=community, name="Mods", slug="mods")
    tools = PackageCategoryFactory(community=community, name="Tools", slug="tools")
    categories = [tools, mods]
    listing = PackageListingFactory(community_=community, package_=package)
    listing.categories.set([tools])
    listing.has_nsfw_content = not desired_nsfw(package, community)
    listing.save(update_fields=("has_nsfw_content",))

    context = ContentPopulatorContext(
        packages=[package],
        communities=[community],
        categories={community.pk: categories},
    )
    ListingPopulator().populate(context)
    ListingPopulator().populate(context)

    listing.refresh_from_db()
    expected_categories = desired_listing_categories(
        package, community, list(reversed(categories))
    )
    assert listing.has_nsfw_content is desired_nsfw(package, community)
    assert set(listing.categories.values_list("pk", flat=True)) == {
        category.pk for category in expected_categories
    }


@pytest.mark.django_db
def test_listing_populator_category_choice_ignores_input_order() -> None:
    community = CommunityFactory()
    package = PackageFactory()
    mods = PackageCategoryFactory(community=community, name="Mods", slug="mods")
    tools = PackageCategoryFactory(community=community, name="Tools", slug="tools")

    forward = desired_listing_categories(package, community, [mods, tools])
    reverse = desired_listing_categories(package, community, [tools, mods])

    assert [category.pk for category in forward] == [
        category.pk for category in reverse
    ]
