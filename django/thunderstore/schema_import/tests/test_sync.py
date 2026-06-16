import pytest

from thunderstore.community.models import (
    Community,
    GameVersion,
    PackageCategory,
    PackageListingSection,
    ReleaseGroup,
)
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models import Package, PackageInstaller
from thunderstore.schema_import.schema import (
    Schema,
    SchemaCommunity,
    SchemaPackageInstaller,
    SchemaThunderstoreGameVersion,
    SchemaThunderstoreReleaseGroup,
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
def test_import_game_versions_from_community():
    schema = Schema(
        schemaVersion="0.0.1",
        games=dict(),
        communities={
            "test": SchemaCommunity(
                displayName="Test community",
                categories=dict(),
                sections=dict(),
                gameVersions=[
                    SchemaThunderstoreReleaseGroup(
                        slug="3.0",
                        displayName="3.0.x",
                        order=5,
                        versions=[
                            SchemaThunderstoreGameVersion(
                                version="3.0.0",
                                releaseName=None,
                                order=10,
                                isActive=True,
                            )
                        ],
                    ),
                    SchemaThunderstoreReleaseGroup(
                        slug="2.0",
                        displayName="2.0.x",
                        releaseName=None,
                        versions=[
                            SchemaThunderstoreGameVersion(
                                version="2.0.0",
                                releaseName=None,
                                isActive=False,
                            )
                        ],
                    ),
                    SchemaThunderstoreReleaseGroup(
                        slug="1.0",
                        displayName="1.0.x",
                        releaseName="Initial Release",
                        versions=[
                            SchemaThunderstoreGameVersion(
                                version="1.0.0",
                                releaseName="Initial Release",
                                isActive=True,
                            ),
                            SchemaThunderstoreGameVersion(
                                version="1.0.1",
                            ),
                        ],
                    ),
                ],
            ),
        },
        packageInstallers=dict(),
    )
    import_schema_communities(schema)
    assert ReleaseGroup.objects.count() == 3
    assert GameVersion.objects.count() == 4

    group_3_0 = ReleaseGroup.objects.get(slug="3.0")
    assert group_3_0.display_name == "3.0.x"
    assert group_3_0.release_name is None
    assert group_3_0.order == 5
    version_3_0_0 = GameVersion.objects.get(version="3.0.0", release_group=group_3_0)
    assert version_3_0_0.release_name is None
    assert version_3_0_0.order == 10
    assert version_3_0_0.is_active is True

    group_2_0 = ReleaseGroup.objects.get(slug="2.0")
    assert group_2_0.display_name == "2.0.x"
    assert group_2_0.release_name is None
    assert group_2_0.order == 1
    version_2_0_0 = GameVersion.objects.get(version="2.0.0", release_group=group_2_0)
    assert version_2_0_0.release_name is None
    assert version_2_0_0.order == 0
    assert version_2_0_0.is_active is False

    group_1_0 = ReleaseGroup.objects.get(slug="1.0")
    assert group_1_0.display_name == "1.0.x"
    assert group_1_0.release_name == "Initial Release"
    assert group_1_0.order == 0
    version_1_0_0 = GameVersion.objects.get(version="1.0.0", release_group=group_1_0)
    assert version_1_0_0.release_name == "Initial Release"
    assert version_1_0_0.order == 0
    assert version_1_0_0.is_active is True
    version_1_0_1 = GameVersion.objects.get(version="1.0.1", release_group=group_1_0)
    assert version_1_0_1.release_name is None
    assert version_1_0_1.order == 1
    assert version_1_0_1.is_active is True
