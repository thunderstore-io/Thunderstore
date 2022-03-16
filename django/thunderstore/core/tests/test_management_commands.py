import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import override_settings

from thunderstore.community.models import Community, PackageListing
from thunderstore.core.management.commands.create_test_data import CONTENT_POPULATORS
from thunderstore.repository.factories import NamespaceFactory
from thunderstore.repository.models import Package, PackageVersion, Team


@pytest.mark.django_db
@pytest.mark.parametrize("debug", (False, True))
def test_create_test_data_debug_check(debug: bool) -> None:
    @override_settings(DEBUG=debug)
    def test_debug():
        try:
            call_command("create_test_data")
            assert Package.objects.filter(name__icontains="Test_Package").count() == 10
            assert Team.objects.filter(name__icontains="Test_Team").count() == 10
            assert (
                PackageVersion.objects.filter(name__icontains="Test_Package").count()
                == 30
            )
            assert settings.DEBUG is True
        except CommandError as e:
            assert settings.DEBUG is False
            assert "Only executable in debug environments" == str(e)

    test_debug()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_create_test_data_clear() -> None:
    assert settings.DEBUG is True
    team = Team(name="to_be_deleted_team")
    team.save()
    package = Package(
        name="to_be_deleted_package",
        owner=team,
        namespace=NamespaceFactory.create(name=team.name, team=team),
    )
    package.save()
    pv = PackageVersion(
        name="to_be_deleted_package",
        package=package,
        version_number="1.0.0",
        website_url="https://example.org",
        description="Example mod",
        readme="# This is an example mod",
        file_size=5242880,
    )
    pv.save()

    call_command("create_test_data", "--clear")
    teams = Team.objects.all()
    packages = Package.objects.all()
    pvs = PackageVersion.objects.all()
    assert not teams.filter(pk=team.pk).exists()
    assert not packages.filter(pk=package.pk).exists()
    assert not pvs.filter(pk=pv.pk).exists()
    assert teams.filter(name__icontains="Test_Team").count() == 10
    assert packages.filter(name__icontains="Test_Package").count() == 10
    assert pvs.filter(name__icontains="Test_Package").count() == 30


@pytest.mark.django_db
@override_settings(DEBUG=True)
@pytest.mark.parametrize("team_count", (1, 2))
@pytest.mark.parametrize("package_count", (2, 4))
@pytest.mark.parametrize("version_count", (2, 4))
@pytest.mark.parametrize("dependency_count", (1, 2))
def test_create_test_data_create_data(
    community: Community,
    team_count: int,
    package_count: int,
    version_count: int,
    dependency_count: int,
) -> None:
    assert settings.DEBUG is True
    call_command(
        "create_test_data",
        "--team-count",
        team_count,
        "--package-count",
        package_count,
        "--version-count",
        version_count,
        "--dependency-count",
        dependency_count,
    )
    created_teams = Team.objects.filter(name__icontains="Test_Team_")
    created_packages = Package.objects.filter(name__icontains="Test_Package_")
    created_package_versions = PackageVersion.objects.filter(
        name__icontains="Test_Package_"
    )
    assert created_teams.count() == team_count
    assert created_packages.count() == team_count * package_count
    assert (
        created_package_versions.count() == team_count * package_count * version_count
    )
    assert (
        PackageVersion.dependencies.through.objects.count()
        == (team_count * package_count - dependency_count) * dependency_count
    )
    assert (
        PackageListing.objects.filter(package__in=created_packages).count()
        == team_count * package_count
    )
    for t in created_teams:
        assert t.owned_packages.all().count() == package_count
    assert (
        Package.objects.annotate(c=Count("latest__dependencies"))
        .filter(c__exact=0)
        .count()
        == dependency_count
    )
    assert Package.objects.annotate(c=Count("latest__dependencies")).filter(
        c__exact=dependency_count
    ).count() == (team_count * package_count - dependency_count)
    versions = [f"{vernum}.0.0" for vernum in range(version_count)]
    for pv in created_package_versions:
        assert pv.name == pv.package.name
        assert pv.version_number in versions


@override_settings(DEBUG=True)
@pytest.mark.django_db
@pytest.mark.parametrize("populator", CONTENT_POPULATORS.keys())
def test_create_test_data_only_filter_valid(populator: str) -> None:
    # TODO: Verify only matching content was created
    # TODO: Verify combination usage
    call_command(
        "create_test_data",
        "--only",
        populator,
    )


@override_settings(DEBUG=True)
@pytest.mark.django_db
def test_create_test_data_only_filter_invalid() -> None:
    with pytest.raises(
        CommandError, match="Invalid --only selection provided, options are"
    ):
        call_command("create_test_data", "--only", "badfilter")
