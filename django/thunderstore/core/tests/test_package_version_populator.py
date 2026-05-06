import builtins
import importlib
import sys
from unittest.mock import patch

import pytest

from thunderstore.core.management.commands.content.base import ContentPopulatorContext
from thunderstore.core.management.commands.content.package_version import (
    PackageVersionPopulator,
)
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import PackageVersion
from thunderstore.storage.models import DataBlobGroup


@pytest.mark.django_db
def test_package_version_populator_clear_deletes_versions() -> None:
    PackageVersionFactory()
    assert PackageVersion.objects.exists()

    PackageVersionPopulator().clear()

    assert not PackageVersion.objects.exists()


@pytest.mark.django_db
def test_package_version_populator_populate_creates_expected_versions() -> None:
    package = PackageFactory()
    assert package.versions.count() == 0

    context = ContentPopulatorContext(packages=[package], version_count=3)
    PackageVersionPopulator().populate(context)

    versions = list(
        package.versions.order_by("version_number").values_list(
            "version_number", flat=True
        )
    )
    assert versions == ["0.0.0", "1.0.0", "2.0.0"]


@pytest.mark.django_db
def test_package_version_populator_populate_respects_existing_version_count() -> None:
    package = PackageFactory()
    PackageVersionFactory(package=package, name=package.name, version_number="0.0.0")

    context = ContentPopulatorContext(packages=[package], version_count=2)
    PackageVersionPopulator().populate(context)

    versions = list(
        package.versions.order_by("version_number").values_list(
            "version_number", flat=True
        )
    )
    assert versions == ["0.0.0", "1.0.0"]


@pytest.mark.django_db
@pytest.mark.parametrize("reuse_icon", (True, False))
def test_package_version_populator_reuse_icon_behavior(reuse_icon: bool) -> None:
    packages = [PackageFactory(), PackageFactory()]
    context = ContentPopulatorContext(
        packages=packages,
        version_count=2,
        reuse_icon=reuse_icon,
    )

    PackageVersionPopulator().populate(context)

    icon_paths = list(
        PackageVersion.objects.order_by("pk").values_list("icon", flat=True)
    )
    assert len(icon_paths) == 4
    if reuse_icon:
        assert len(set(icon_paths)) == 1
    else:
        assert len(set(icon_paths)) == 4


@pytest.mark.django_db
def test_package_version_populator_seed_skips_without_ts_scanners(
    mocker, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        None,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        None,
    )

    PackageVersionPopulator()._seed_package_source_data()

    out = capsys.readouterr().out
    assert "Skipping package source seed data: ts_scanners is not available." in out


@pytest.mark.django_db
def test_package_version_populator_seed_skips_without_active_version(
    mocker, capsys: pytest.CaptureFixture[str]
) -> None:
    # Real ts_scanners (and its DB tables) may be absent in CI; fakes still hit
    # the query + early-return branch.
    fake_status = mocker.Mock()
    fake_status.SUCCESS = "SUCCESS"
    fake_decompilation = mocker.MagicMock()
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        fake_decompilation,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        fake_status,
    )

    PackageVersion.objects.all().delete()
    assert not PackageVersion.objects.filter(is_active=True).exists()

    PackageVersionPopulator()._seed_package_source_data()

    out = capsys.readouterr().out
    assert "No active package version found for source data seeding." in out
    fake_decompilation.objects.update_or_create.assert_not_called()


@pytest.mark.django_db
def test_package_version_populator_seed_writes_file_tree_and_decompilation_calls(
    mocker, capsys: pytest.CaptureFixture[str]
) -> None:
    """Full seed path without real ts_scanners installed (mocks ORM entrypoints)."""
    fake_status = mocker.Mock()
    fake_status.SUCCESS = "SUCCESS"
    fake_decompilation = mocker.MagicMock()
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        fake_decompilation,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        fake_status,
    )

    version = PackageVersionFactory()
    assert version.file_tree_id is None

    PackageVersionPopulator()._seed_package_source_data()

    version.refresh_from_db()
    assert version.file_tree_id is not None
    assert version.file_tree.is_complete is True

    assert fake_decompilation.objects.update_or_create.call_count == 5
    out = capsys.readouterr().out
    assert f"Seeded package source data for {version.full_version_name}." in out


@pytest.mark.django_db
def test_package_version_populator_seed_reuses_same_file_tree_on_reseed(
    mocker, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_status = mocker.Mock()
    fake_status.SUCCESS = "SUCCESS"
    fake_decompilation = mocker.MagicMock()
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        fake_decompilation,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        fake_status,
    )

    version = PackageVersionFactory()
    populator = PackageVersionPopulator()

    populator._seed_package_source_data()
    version.refresh_from_db()
    first_group_id = version.file_tree_id
    assert first_group_id is not None

    fake_decompilation.objects.update_or_create.reset_mock()
    populator._seed_package_source_data()

    version.refresh_from_db()
    assert version.file_tree_id == first_group_id
    assert version.file_tree.is_complete is True
    assert fake_decompilation.objects.update_or_create.call_count == 5
    out = capsys.readouterr().out
    assert (
        out.count(f"Seeded package source data for {version.full_version_name}.") == 2
    )


@pytest.mark.django_db
def test_package_version_populator_seed_replaces_mismatched_file_tree(
    mocker,
) -> None:
    fake_status = mocker.Mock()
    fake_status.SUCCESS = "SUCCESS"
    fake_decompilation = mocker.MagicMock()
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        fake_decompilation,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        fake_status,
    )

    version = PackageVersionFactory()
    wrong_tree = DataBlobGroup.objects.create(name="Wrong file tree label")
    version.file_tree = wrong_tree
    version.save(update_fields=("file_tree",))

    PackageVersionPopulator()._seed_package_source_data()

    version.refresh_from_db()
    expected_name = f"File tree of package: {version.full_version_name}"
    assert version.file_tree.name == expected_name
    assert version.file_tree_id != wrong_tree.pk
    assert not DataBlobGroup.objects.filter(pk=wrong_tree.pk).exists()


@pytest.mark.django_db
def test_package_version_populator_seed_attaches_orphan_group_with_matching_name(
    mocker,
) -> None:
    fake_status = mocker.Mock()
    fake_status.SUCCESS = "SUCCESS"
    fake_decompilation = mocker.MagicMock()
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.Decompilation",
        fake_decompilation,
    )
    mocker.patch(
        "thunderstore.core.management.commands.content.package_version.DecompilationStatus",
        fake_status,
    )

    version = PackageVersionFactory()
    tree_name = f"File tree of package: {version.full_version_name}"
    orphan = DataBlobGroup.objects.create(name=tree_name)
    assert version.file_tree_id is None

    PackageVersionPopulator()._seed_package_source_data()

    version.refresh_from_db()
    assert version.file_tree_id == orphan.pk
    assert version.file_tree.is_complete is True


def test_package_version_module_reraises_non_ts_scanners_module_not_found() -> None:
    mod_name = "thunderstore.core.management.commands.content.package_version"
    sys.modules.pop(mod_name, None)
    real_import = builtins.__import__

    def import_hook(
        name: str,
        globalns=None,
        localns=None,
        fromlist=(),
        level: int = 0,
    ):
        if name == "ts_scanners.models.decompilation":
            raise ModuleNotFoundError(name="some_transitive_dependency")
        return real_import(name, globalns, localns, fromlist, level)

    try:
        with patch("builtins.__import__", side_effect=import_hook):
            with pytest.raises(ModuleNotFoundError) as excinfo:
                importlib.import_module(mod_name)
        assert excinfo.value.name == "some_transitive_dependency"
    finally:
        sys.modules.pop(mod_name, None)
        importlib.import_module(mod_name)


def test_package_version_module_sets_decompilation_none_when_import_fails() -> None:
    mod_name = "thunderstore.core.management.commands.content.package_version"
    sys.modules.pop(mod_name, None)
    real_import = builtins.__import__

    def import_hook(
        name: str,
        globalns=None,
        localns=None,
        fromlist=(),
        level: int = 0,
    ):
        if name == "ts_scanners.models.decompilation":
            raise ModuleNotFoundError(name="ts_scanners")
        return real_import(name, globalns, localns, fromlist, level)

    try:
        with patch("builtins.__import__", side_effect=import_hook):
            mod = importlib.import_module(mod_name)
        assert mod.Decompilation is None
        assert mod.DecompilationStatus is None
    finally:
        sys.modules.pop(mod_name, None)
        importlib.import_module(mod_name)
