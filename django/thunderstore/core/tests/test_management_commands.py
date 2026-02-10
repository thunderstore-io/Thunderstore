import io

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import override_settings

from django_contracts.models import LegalContract, LegalContractVersion
from thunderstore.community.models import Community, CommunitySite, PackageListing
from thunderstore.core.management.commands.create_test_data import CONTENT_POPULATORS
from thunderstore.repository.factories import NamespaceFactory
from thunderstore.repository.models import Package, PackageVersion, Team
from thunderstore.wiki.models import WikiPage


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
@pytest.mark.parametrize("community_count", (2, 4))
@pytest.mark.parametrize("version_count", (2, 4))
@pytest.mark.parametrize("dependency_count", (1, 2))
@pytest.mark.parametrize("legal_contract_count", (2,))
@pytest.mark.parametrize("legal_contract_version_count", (4,))
@pytest.mark.parametrize("wiki_page_count", (4,))
def test_create_test_data_create_data(
    community: Community,
    team_count: int,
    package_count: int,
    community_count: int,
    version_count: int,
    dependency_count: int,
    legal_contract_count: int,
    legal_contract_version_count: int,
    wiki_page_count: int,
) -> None:
    assert settings.DEBUG is True

    def assert_counts():
        created_teams = Team.objects.filter(name__icontains="Test_Team_")
        created_packages = Package.objects.filter(name__icontains="Test_Package_")
        created_package_versions = PackageVersion.objects.filter(
            name__icontains="Test_Package_"
        )
        created_communities = Community.objects.filter(
            identifier__startswith="test-community-"
        )
        created_community_sites = CommunitySite.objects.filter(
            community__identifier__startswith="test-community-"
        )
        created_contracts = LegalContract.objects.filter(
            slug__startswith="test-contract-",
        )
        created_contract_versions = LegalContractVersion.objects.filter(
            markdown_content__startswith="## Test Contract "
        )
        created_wiki_pages = WikiPage.objects.filter(title__startswith="Test Page ")
        assert created_teams.count() == team_count
        assert created_packages.count() == team_count * package_count
        assert (
            created_wiki_pages.count() == package_count * team_count * wiki_page_count
        )
        assert created_communities.count() == community_count
        assert created_community_sites.count() == community_count
        assert created_contracts.count() == legal_contract_count
        assert (
            created_contract_versions.count()
            == legal_contract_count * legal_contract_version_count
        )
        assert (
            created_package_versions.count()
            == team_count * package_count * version_count
        )
        assert (
            PackageVersion.dependencies.through.objects.count()
            == (team_count * package_count - dependency_count) * dependency_count
        )
        assert (
            PackageListing.objects.filter(package__in=created_packages).count()
            == team_count * package_count * community_count
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

    args = [
        "create_test_data",
        "--team-count",
        team_count,
        "--package-count",
        package_count,
        "--wiki-page-count",
        wiki_page_count,
        "--community-count",
        community_count,
        "--version-count",
        version_count,
        "--dependency-count",
        dependency_count,
        "--contract-count",
        legal_contract_count,
        "--contract-version-count",
        legal_contract_version_count,
    ]
    call_command(*args)
    assert_counts()
    # The data creation should be idempotent, so calling it again should result
    # in the same data distribution.
    call_command(*args)
    assert_counts()


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


@override_settings(DEBUG=True)
@pytest.mark.django_db
@pytest.mark.parametrize("reuse", (True, False))
def test_create_test_data_reuse_icon(reuse: bool) -> None:
    args = [
        "create_test_data",
        "--community-count",
        1,
        "--team-count",
        1,
        "--package-count",
        1,
        "--version-count",
        2,
        "--dependency-count",
        0,
        "--wiki-page-count",
        0,
        "--contract-count",
        0,
        "--contract-version-count",
        0,
    ]
    if reuse:
        args.append("--reuse-icon")

    assert not PackageVersion.objects.exists()

    call_command(*args)
    icon_paths = PackageVersion.objects.values_list("icon", flat=True)

    assert len(icon_paths) == 2
    assert (icon_paths[0] == icon_paths[1]) == reuse


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_setup_dev_env_requires_debug() -> None:
    with pytest.raises(
        CommandError, match="setup_dev_env can only run when DEBUG=True"
    ):
        call_command("setup_dev_env")


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_setup_dev_env_populates_sites_binds_community_and_creates_admin(
    mocker,
) -> None:
    recorded_calls = []

    def fake_call_command(*args, **kwargs):
        recorded_calls.append((args, kwargs))
        return None

    mocker.patch(
        "thunderstore.core.management.commands.setup_dev_env.call_command",
        side_effect=fake_call_command,
    )

    # Seed some existing state that should be updated/removed
    Site.objects.update_or_create(domain="*", defaults={"name": "Wildcard"})
    Site.objects.update_or_create(domain="example.com", defaults={"name": "Example"})
    Site.objects.update_or_create(
        domain="thunderstore.localhost", defaults={"name": "Old Thunderstore"}
    )
    Site.objects.update_or_create(
        domain="auth.thunderstore.localhost", defaults={"name": "Old Thunderstore Auth"}
    )

    other_community = Community.objects.create(identifier="other", name="Other")
    other_site = Site.objects.create(
        domain="other.thunderstore.localhost", name="Other"
    )
    CommunitySite.objects.create(site=other_site, community=other_community)

    assert get_user_model().objects.filter(username="admin").exists() is False

    call_command("setup_dev_env")

    # Verify command orchestration calls
    assert ("migrate",) in [c[0] for c in recorded_calls]
    assert ("create_test_data", "--clear", "--reuse-icon") in [
        c[0] for c in recorded_calls
    ]

    # Verify sites were upserted and extras removed
    assert set(Site.objects.values_list("domain", flat=True)) == {
        "thunderstore.localhost",
        "auth.thunderstore.localhost",
    }
    assert Site.objects.get(domain="thunderstore.localhost").name == "Thunderstore"
    assert (
        Site.objects.get(domain="auth.thunderstore.localhost").name
        == "Thunderstore Auth"
    )

    # Verify community binding
    community = Community.objects.get(identifier="riskofrain2")
    localhost_site = Site.objects.get(domain="thunderstore.localhost")
    assert CommunitySite.objects.count() == 1
    assert CommunitySite.objects.filter(
        site=localhost_site, community=community
    ).exists()

    # Verify admin user created
    admin_user = get_user_model().objects.get(username="admin")
    assert admin_user.is_superuser is True
    assert admin_user.is_staff is True


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_setup_dev_env_skip_test_data_skips_create_test_data(mocker) -> None:
    recorded_calls = []

    def fake_call_command(*args, **kwargs):
        recorded_calls.append((args, kwargs))
        return None

    mocker.patch(
        "thunderstore.core.management.commands.setup_dev_env.call_command",
        side_effect=fake_call_command,
    )

    call_command("setup_dev_env", "--skip-test-data")

    called_commands = [c[0][0] for c in recorded_calls]
    assert "migrate" in called_commands
    assert "create_test_data" not in called_commands


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_setup_dev_env_admin_already_exists_does_not_create_superuser(mocker) -> None:
    User = get_user_model()
    User.objects.create_user("admin", "admin@example.com", "password")

    recorded_calls = []

    def fake_call_command(*args, **kwargs):
        recorded_calls.append((args, kwargs))
        return None

    mocker.patch(
        "thunderstore.core.management.commands.setup_dev_env.call_command",
        side_effect=fake_call_command,
    )

    create_superuser_mock = mocker.patch.object(User.objects, "create_superuser")
    stdout = io.StringIO()

    call_command("setup_dev_env", stdout=stdout)

    create_superuser_mock.assert_not_called()
    assert "Superuser 'admin' already exists." in stdout.getvalue()
