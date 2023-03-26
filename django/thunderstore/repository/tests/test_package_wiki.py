import pytest

from thunderstore.repository.models import (
    Package,
    PackageVersion,
    PackageWiki,
    create_wiki_for_package,
)


@pytest.mark.django_db
@pytest.mark.parametrize("save", (False, True))
def test_package_wiki_get_for_package_existing(package: Package, save: bool):
    result = create_wiki_for_package(package, save)
    assert (result.pk is None) is not save


@pytest.mark.django_db
@pytest.mark.parametrize("create", (False, True))
@pytest.mark.parametrize("dummy", (False, True))
def test_package_wiki_get_for_package_existing(
    package_version: PackageVersion,
    package_wiki: PackageWiki,
    create: bool,
    dummy: bool,
):
    assert (
        PackageWiki.get_for_package(package_version.package, create, dummy)
        == package_wiki
    )


@pytest.mark.django_db
@pytest.mark.parametrize("create", (False, True))
@pytest.mark.parametrize("dummy", (False, True))
def test_package_wiki_get_for_package_nonexisting(
    package_version: PackageVersion,
    create: bool,
    dummy: bool,
):
    result = PackageWiki.get_for_package(package_version.package, create, dummy)

    if dummy or create:
        assert result is not None
    else:
        assert result is None

    if dummy and not create:
        assert result.pk is None
    if create:
        assert result.pk is not None
