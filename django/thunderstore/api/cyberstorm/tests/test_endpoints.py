import pytest

from thunderstore.api.cyberstorm.tests.endpoint_data import (
    DELETE_TEST_CASES,
    GET_TEST_CASES,
    PATCH_TEST_CASES,
    POST_TEST_CASES,
)
from thunderstore.api.cyberstorm.tests.utils import (
    convert_path_to_schema_style,
    extract_paths,
    fill_path_params,
    get_resolver,
    get_schema,
    validate_request_body_against_schema,
    validate_response_against_schema,
)
from thunderstore.api.urls import cyberstorm_urls
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import PackageListing, TeamMemberRole


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
def test_cyberstorm_GET_endpoint_schemas(
    test_case, api_client, active_package_listing, package_category
):
    api_path = test_case["path"]
    user = setup_superuser_with_package(active_package_listing, package_category)
    api_client.force_authenticate(user)

    param_values = get_parameter_values(active_package_listing)
    schema = get_schema(api_client)
    resolver = get_resolver(schema)

    url = fill_path_params(api_path, param_values)
    response = api_client.get(url, format="json")

    errors = validate_response_against_schema(
        response=response,
        path=api_path,
        method="get",
        schema=schema,
        resolver=resolver,
    )

    if errors:
        pytest.fail(f"Validation errors for GET {api_path}:\n" + "\n".join(errors))


@pytest.mark.django_db
@pytest.mark.parametrize("test_case", DELETE_TEST_CASES)
def test_cyberstorm_DELETE_endpoint_schemas(
    test_case, api_client, active_package_listing, package_category, service_account
):
    api_path = test_case["path"]
    user = setup_superuser_with_package(active_package_listing, package_category)
    api_client.force_authenticate(user)

    service_account.team = active_package_listing.package.owner
    service_account.save()

    param_values = get_parameter_values(active_package_listing)
    schema = get_schema(api_client)
    resolver = get_resolver(schema)

    url = fill_path_params(api_path, param_values)

    if "disband" in api_path:
        user.teams.first().team.owned_packages.all().delete()

    response = api_client.delete(url, format="json")

    errors = validate_response_against_schema(
        response=response,
        path=api_path,
        method="delete",
        schema=schema,
        resolver=resolver,
    )

    if errors:
        pytest.fail(f"Validation errors for DELETE {api_path}:\n" + "\n".join(errors))


@pytest.mark.django_db
@pytest.mark.parametrize("test_case", POST_TEST_CASES)
def test_cyberstorm_POST_endpoint_schemas(
    test_case, api_client, active_package_listing, package_category
):
    api_path = test_case["path"]
    payload = test_case["payload"]
    user = setup_superuser_with_package(active_package_listing, package_category)
    api_client.force_authenticate(user)

    param_values = get_parameter_values(active_package_listing)
    schema = get_schema(api_client)
    resolver = get_resolver(schema)
    failures = []

    request_errors = validate_request_body_against_schema(
        request_body=payload,
        path=api_path,
        method="post",
        schema=schema,
        resolver=resolver,
    )

    if request_errors:
        failures.extend(request_errors)

    url = fill_path_params(api_path, param_values)
    response = api_client.post(url, data=payload, format="json")

    response_errors = validate_response_against_schema(
        response=response,
        path=api_path,
        method="post",
        schema=schema,
        resolver=resolver,
    )

    if response_errors:
        failures.extend(response_errors)

    if failures:
        pytest.fail("\n".join(failures))


@pytest.mark.django_db
@pytest.mark.parametrize("test_case", PATCH_TEST_CASES)
def test_cyberstorm_PATCH_endpoint_schemas(
    test_case, api_client, active_package_listing, package_category
):
    api_path = test_case["path"]
    payload = test_case["payload"]
    user = setup_superuser_with_package(active_package_listing, package_category)
    api_client.force_authenticate(user)

    param_values = get_parameter_values(active_package_listing)
    schema = get_schema(api_client)
    resolver = get_resolver(schema)
    failures = []

    request_errors = validate_request_body_against_schema(
        request_body=payload,
        path=api_path,
        method="patch",
        schema=schema,
        resolver=resolver,
    )

    if request_errors:
        failures.extend(request_errors)

    url = fill_path_params(api_path, param_values)
    response = api_client.patch(url, data=payload, format="json")

    response_errors = validate_response_against_schema(
        response=response,
        path=api_path,
        method="patch",
        schema=schema,
        resolver=resolver,
    )

    if response_errors:
        failures.extend(response_errors)

    if failures:
        pytest.fail("\n".join(failures))


@pytest.mark.django_db
def test_validate_extracted_paths_with_urlpatterns(api_client):
    schema = get_schema(api_client)
    existing_paths = [
        convert_path_to_schema_style(f"/api/cyberstorm/{url.pattern}")
        for url in cyberstorm_urls
    ]

    extracted_paths = extract_paths(schema, "cyberstorm")
    assert set(existing_paths) == set(extracted_paths)


@pytest.mark.django_db
def test_find_missing_endpoints():
    tested_paths = {
        convert_path_to_schema_style(path["path"])
        for path in GET_TEST_CASES
        + POST_TEST_CASES
        + PATCH_TEST_CASES
        + DELETE_TEST_CASES
    }

    existing_paths = {
        convert_path_to_schema_style(f"/api/cyberstorm/{url.pattern}")
        for url in cyberstorm_urls
    }

    missing = existing_paths - tested_paths

    if missing:
        pytest.fail("Missing test coverage for:\n" + "\n".join(sorted(missing)))
