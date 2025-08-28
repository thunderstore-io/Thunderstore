import factory
import pytest

from thunderstore.account.forms import CreateServiceAccountForm
from thunderstore.api.cyberstorm.tests.endpoint_data import GET_TEST_CASES
from thunderstore.community.models import Community
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import (
    PackageListing,
    Team,
    TeamMember,
    TeamMemberRole,
)

from .utils import (
    fill_path_params,
    setup_superuser,
    setup_superuser_with_package,
    validate_max_queries,
)

MAX_QUERIES = 15


def get_parameter_values(package_listing: PackageListing) -> dict:
    service_account = package_listing.package.owner.service_accounts.first()

    return {
        "community_id": package_listing.community.identifier,
        "namespace_id": package_listing.package.owner.get_namespace().name,
        "package_name": package_listing.package.name,
        "version_number": package_listing.package.latest.version_number,
        "team_id": package_listing.package.owner.name,
        "team_name": package_listing.package.owner.name,
        "uuid": service_account.uuid if service_account else "",
    }


@pytest.mark.django_db
@pytest.mark.parametrize("test_case", GET_TEST_CASES)
def test_cyberstorm_api_GET_query_count(
    test_case, api_client, active_package_listing, package_category
):
    api_path = test_case["path"]
    user = setup_superuser_with_package(active_package_listing, package_category)
    api_client.force_authenticate(user)
    param_values = get_parameter_values(active_package_listing)
    url = fill_path_params(api_path, param_values)

    validate_max_queries(
        client=api_client,
        method="get",
        path=url,
        max_queries=MAX_QUERIES,
    )


@pytest.mark.django_db
def test_cybserstorm_community_list_query_count(api_client):
    path = "/api/cyberstorm/community/"

    communities = []

    for x in range(20):
        random_name = f"Community_{x}"
        random_id = f"community_{x}"
        communities.append(Community(name=random_name, identifier=random_id))

    Community.objects.bulk_create(communities)

    validate_max_queries(
        client=api_client,
        method="get",
        path=path,
        max_queries=MAX_QUERIES,
    )


@pytest.mark.django_db
def test_cyberstorm_package_versions_list_query_count(api_client, active_package):
    url = "/api/cyberstorm/package/{namespace_id}/{package_name}/versions/"

    PackageVersionFactory.create_batch(
        20,
        package=active_package,
        name=factory.Sequence(lambda n: f"{active_package.name}_2_0_{n+1}"),
        version_number=factory.Sequence(lambda n: f"2.0.{n+1}"),
        website_url="https://example.org",
        description="Example mod",
        readme="# This is an example mod",
        changelog="# This is an example changelog",
    )

    user = setup_superuser()
    api_client.force_authenticate(user)
    path_params = {
        "namespace_id": active_package.owner.get_namespace().name,
        "package_name": active_package.name,
    }
    path = fill_path_params(url, path_params)

    validate_max_queries(
        client=api_client,
        method="get",
        path=path,
        max_queries=MAX_QUERIES,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_case",
    [
        {"path": "/api/cyberstorm/listing/{community_id}/"},
        {"path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/"},
    ],
)
def test_cyberstorm_package_listing_list_query_count(test_case, api_client):
    amount = 20
    community = Community.objects.create(
        name="Test_Community", identifier="test_community"
    )
    team = Team.create(name="Test_Team")
    namespace = team.get_namespace()

    packages = PackageFactory.create_batch(
        amount,
        is_active=True,
        is_deprecated=False,
        owner=team,
        namespace=namespace,
        name=factory.Sequence(lambda n: f"Test_Package_{n}"),
    )

    PackageVersionFactory.create_batch(
        amount,
        package=factory.Iterator(packages),
        name=factory.Iterator([pkg.name for pkg in packages]),
        is_active=True,
    )

    PackageListing.objects.bulk_create(
        [PackageListing(community=community, package=pkg) for pkg in packages]
    )

    api_path = test_case["path"]
    user = setup_superuser()
    api_client.force_authenticate(user)
    path_params = {
        "community_id": community.identifier,
        "namespace_id": namespace.name,
    }
    url = fill_path_params(api_path, path_params)

    validate_max_queries(
        client=api_client,
        method="get",
        path=url,
        max_queries=MAX_QUERIES,
    )


@pytest.mark.django_db
def test_cyberstorm_team_member_list_query_count(api_client):
    url = "/api/cyberstorm/team/{team_id}/member/"
    user = setup_superuser()
    team = Team.create(name="Test_Team")

    users = UserFactory.create_batch(20)
    TeamMember.objects.bulk_create(
        [
            TeamMember(team=team, user=member_user, role=TeamMemberRole.member)
            for member_user in users
        ]
    )

    api_client.force_authenticate(user)
    url = fill_path_params(url, {"team_id": team.name})

    validate_max_queries(
        client=api_client,
        method="get",
        path=url,
        max_queries=MAX_QUERIES,
    )


@pytest.mark.django_db
def test_cyberstorm_team_service_accounts_list_query_count(api_client):
    url = "/api/cyberstorm/team/{team_id}/service-account/"
    user = setup_superuser()

    team = Team.create(name="Test_Team")
    team.add_member(user=user, role=TeamMemberRole.owner)

    for x in range(20):
        member_user = UserFactory.create(username=f"TestUser_{x+1}")
        team.add_member(user=member_user, role=TeamMemberRole.owner)
        form = CreateServiceAccountForm(
            user,
            data={"team": team, "nickname": f"ServiceAccount_{x}"},
        )
        form.is_valid()
        form.save()

    api_client.force_authenticate(user)
    path_params = {"team_id": team.name}
    url = fill_path_params(url, path_params)

    validate_max_queries(
        client=api_client,
        method="get",
        path=url,
        max_queries=MAX_QUERIES,
    )
