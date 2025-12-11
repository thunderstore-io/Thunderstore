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
def test_import_categories_hidden_flag():
    schema = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories={
                    "visible": {"label": "Visible", "hidden": False},
                    "hidden": {"label": "Hidden Cat", "hidden": True},
                },
                sections=dict(),
                shortDescription=None,
                discordUrl=None,
                wikiUrl=None,
                autolistPackageIds=None,
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema)
    community = Community.objects.get(identifier="test")
    cats = {c.slug: c for c in community.package_categories.all()}
    assert cats["visible"].hidden is False
    assert cats["hidden"].hidden is True
