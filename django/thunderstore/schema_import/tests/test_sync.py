import pytest

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models import Package, PackageInstaller
from thunderstore.schema_import.schema import (
    Schema,
    SchemaCommunity,
    SchemaPackageInstaller,
    SchemaThunderstoreCategory,
    SchemaThunderstoreSection,
)
from thunderstore.schema_import.sync import (
    get_slogan_from_display_name,
    import_schema_communities,
    import_schema_package_installers,
)
from thunderstore.schema_import.tasks import sync_ecosystem_schema


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("Risk of Rain 2", "The Risk of Rain 2 Mod Database"),
        ("The Ouroboros King", "The Ouroboros King Mod Database"),
    ),
)
def test_schema_sync_slogan_name(name: str, expected: str):
    assert get_slogan_from_display_name(name) == expected


@pytest.mark.django_db
def test_schema_sync():
    assert Community.objects.count() == 0
    assert PackageCategory.objects.count() == 0
    assert PackageListingSection.objects.count() == 0
    assert PackageListing.objects.filter(is_auto_imported=True).count() == 0

    sync_ecosystem_schema.delay()

    com_count = Community.objects.count()
    cat_count = PackageCategory.objects.count()
    sec_count = PackageListingSection.objects.count()

    assert com_count > 0
    assert cat_count > 0
    assert sec_count > 0

    # Ensure idempotency
    sync_ecosystem_schema.delay()

    assert com_count == Community.objects.count()
    assert cat_count == PackageCategory.objects.count()
    assert sec_count == PackageListingSection.objects.count()


@pytest.mark.django_db
def test_import_schema_installers():
    schema = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities=dict(),
        packageInstallers={
            "foo": SchemaPackageInstaller(
                name="Foo installer",
                description="This installs foo packages",
            ),
        },
    )
    assert PackageInstaller.objects.count() == 0
    import_schema_package_installers(schema)
    assert PackageInstaller.objects.count() == 1
    assert PackageInstaller.objects.first().identifier == "foo"


@pytest.mark.django_db
def test_import_autolisted_packages(active_package: Package):
    schema = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories=dict(),
                sections=dict(),
                autolistPackageIds=[active_package.full_package_name],
            ),
        },
        packageInstallers=dict(),
    )
    assert PackageListing.objects.filter(is_auto_imported=True).count() == 0
    import_schema_communities(schema)
    assert PackageListing.objects.filter(is_auto_imported=True).count() == 1


@pytest.mark.django_db
def test_import_deletes_empty_categories():
    schema_with_two_categories = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories={
                    "cat-a": SchemaThunderstoreCategory(label="Category A"),
                    "cat-b": SchemaThunderstoreCategory(label="Category B"),
                },
                sections=dict(),
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_two_categories)
    assert PackageCategory.objects.count() == 2

    schema_with_one_category = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories={
                    "cat-a": SchemaThunderstoreCategory(label="Category A"),
                },
                sections=dict(),
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_one_category)
    assert PackageCategory.objects.count() == 1
    assert PackageCategory.objects.filter(slug="cat-a").exists()
    assert not PackageCategory.objects.filter(slug="cat-b").exists()


@pytest.mark.django_db
def test_import_preserves_non_empty_categories(active_package: Package):
    schema_with_two_categories = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories={
                    "cat-a": SchemaThunderstoreCategory(label="Category A"),
                    "cat-b": SchemaThunderstoreCategory(label="Category B"),
                },
                sections=dict(),
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_two_categories)
    community = Community.objects.get(identifier="test")
    category_b = PackageCategory.objects.get(slug="cat-b", community=community)

    listing = PackageListing.objects.create(package=active_package, community=community)
    listing.categories.add(category_b)

    schema_with_one_category = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories={
                    "cat-a": SchemaThunderstoreCategory(label="Category A"),
                },
                sections=dict(),
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_one_category)

    assert PackageCategory.objects.count() == 2
    assert PackageCategory.objects.filter(slug="cat-b").exists()


@pytest.mark.django_db
def test_import_deletes_removed_sections():
    schema_with_two_sections = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories=dict(),
                sections={
                    "sec-a": SchemaThunderstoreSection(name="Section A"),
                    "sec-b": SchemaThunderstoreSection(name="Section B"),
                },
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_two_sections)
    assert PackageListingSection.objects.count() == 2

    schema_with_one_section = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories=dict(),
                sections={
                    "sec-a": SchemaThunderstoreSection(name="Section A"),
                },
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema_with_one_section)
    assert PackageListingSection.objects.count() == 1
    assert PackageListingSection.objects.filter(slug="sec-a").exists()
    assert not PackageListingSection.objects.filter(slug="sec-b").exists()
