import pytest

from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import PackageListing, TeamMemberRole

from .utils import assert_max_queries, fill_path_params

# TODO: Adjust this value as necessary
MAX_QUERIES = 10

# TODO: Fix this when https://github.com/thunderstore-io/Thunderstore/pull/1098/ is merged
GET_TEST_CASES = [
    {"path": "/api/cyberstorm/community/"},
    {"path": "/api/cyberstorm/community/{community_id}/"},
    {"path": "/api/cyberstorm/community/{community_id}/filters/"},
    {"path": "/api/cyberstorm/listing/{community_id}/"},
    {"path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/"},
    {"path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/"},
    {
        "path": "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/dependants/"
    },
    {
        "path": "/api/cyberstorm/package/{community_id}/{namespace_id}/{package_name}/permissions/"
    },
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/changelog/"},
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/latest/readme/"},
    {
        "path": "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/changelog/"
    },
    {
        "path": "/api/cyberstorm/package/{namespace_id}/{package_name}/v/{version_number}/readme/"
    },
    {"path": "/api/cyberstorm/package/{namespace_id}/{package_name}/versions/"},
    {"path": "/api/cyberstorm/team/{team_id}/"},
    {"path": "/api/cyberstorm/team/{team_id}/member/"},
    {"path": "/api/cyberstorm/team/{team_id}/service-account/"},
]


# TODO: Fix this when https://github.com/thunderstore-io/Thunderstore/pull/1098/ is merged
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


# TODO: Fix this when https://github.com/thunderstore-io/Thunderstore/pull/1098/ is merged
def setup_superuser_with_package(package_listing, package_category=None):
    user = UserFactory()
    user.is_superuser = True
    user.save()
    UserFactory.create(username="TestUser", email="test@user.dev", is_active=True)
    package_listing.package.owner.add_member(
        user=user,
        role=TeamMemberRole.owner,
    )
    if package_category:
        package_category.community = package_listing.community
        package_category.save()
    package_listing.package.latest.changelog = "# This is an example changelog"
    package_listing.package.latest.readme = "# This is an example readme"
    package_listing.package.latest.save()
    return user


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

    assert_max_queries(
        client=api_client,
        method="get",
        path=url,
        max_queries=MAX_QUERIES,
    )
