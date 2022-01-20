import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import override_settings

from thunderstore.repository.factories import NamespaceFactory
from thunderstore.repository.models import Package, PackageVersion, Team


@pytest.mark.django_db
@pytest.mark.parametrize("debug", (False, True))
def test_create_test_data_debug_check(debug):
    @override_settings(DEBUG=debug)
    def test_debug():
        try:
            call_command("create_test_data", 10)
            assert Package.objects.filter(name__icontains="Test_Package").count() == 10
            assert Team.objects.filter(name__icontains="Test_Team").count() == 10
            assert (
                PackageVersion.objects.filter(name__icontains="Test_Package").count()
                == 30
            )
            assert settings.DEBUG == True
        except CommandError as e:
            assert settings.DEBUG == False
            assert "Only executable in debug environments" == str(e)

    test_debug()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_create_test_data_clear():
    assert settings.DEBUG == True
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

    call_command("create_test_data", 10, "--clear")
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
def test_create_test_data_create_data():
    assert settings.DEBUG == True
    call_command("create_test_data", 10)
    created_teams = Team.objects.filter(name__icontains="Test_Team_")
    created_packages = Package.objects.filter(name__icontains="Test_Package_")
    created_package_versions = PackageVersion.objects.filter(
        name__icontains="Test_Package_"
    )
    assert created_teams.count() == 10
    assert created_packages.count() == 10
    assert created_package_versions.count() == 30
    for t in created_teams:
        assert t.owned_packages.all().count() == 1
    assert (
        Package.objects.annotate(c=Count("latest__dependencies"))
        .filter(c__exact=0)
        .count()
        == 2
    )
    assert (
        Package.objects.annotate(c=Count("latest__dependencies"))
        .filter(c__exact=2)
        .count()
        == 8
    )
    for pv in created_package_versions:
        assert pv.name == pv.package.name
        assert pv.version_number in ("0.0.0", "1.0.0", "2.0.0")
