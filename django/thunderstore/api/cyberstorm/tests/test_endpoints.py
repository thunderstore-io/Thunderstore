import pytest

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

post_payload_map = {
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/approve/": {
        "internal_notes": "This is an example internal note",
    },
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/reject/": {
        "rejection_reason": "This is an example rejection reason",
    },
    "/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/update/": {
        "categories": ["test"],
    },
    "/api/cyberstorm/package/{namespace_id}/{package_name}/deprecate/": {
        "deprecate": True,
    },
    "/api/cyberstorm/package/{namespace_id}/{package_name}/rate/": {
        "target_state": "rated"
    },
    "/api/cyberstorm/team/create/": {
        "name": "TestTeam",
    },
    "/api/cyberstorm/team/{team_name}/member/add/": {
        "username": "TestUser",
        "role": "member",
    },
}


put_payload_map = {}


patch_payload_map = {
    "/api/cyberstorm/team/{team_name}/update/": {
        "donation_link": "https://example.com/donate",
    }
}


payload_mapping = {
    "post": post_payload_map,
    "put": put_payload_map,
    "patch": patch_payload_map,
}


def get_parameter_values(package_listing: PackageListing) -> dict:
    return {
        "community_id": package_listing.community.identifier,
        "namespace_id": package_listing.package.owner.get_namespace().name,
        "package_name": package_listing.package.name,
        "version_number": package_listing.package.latest.version_number,
        "team_id": package_listing.package.owner.name,
        "team_name": package_listing.package.owner.name,
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


def make_request(method: str, url: str, api_client, data: dict = {}):
    method = method.lower()
    client_method = getattr(api_client, method)

    if method in ["get", "delete"]:
        return client_method(url)
    else:
        return client_method(url, data=data, format="json")


@pytest.mark.django_db
@pytest.mark.parametrize("http_verb", ["get", "delete", "post", "put", "patch"])
def test_cyberstorm_endpoint_schemas(
    api_client, active_package_listing, package_category, http_verb
):
    user = setup_superuser_with_package(active_package_listing, package_category)
    param_values = get_parameter_values(active_package_listing)
    schema = get_schema(api_client)
    resolver = get_resolver(schema)
    api_paths = extract_paths(schema, "cyberstorm", http_verb)
    matched_payload_map = payload_mapping.get(http_verb)

    request_body = {}
    failures = []

    for path in api_paths:
        url = fill_path_params(path, param_values)
        api_client.force_authenticate(user)

        if matched_payload_map:
            request_body = matched_payload_map.get(path, {})
            errors = validate_request_body_against_schema(
                request_body=request_body,
                path=path,
                method=http_verb,
                schema=schema,
                resolver=resolver,
            )

            failures.extend(errors)

        if "disband" in path:  # requires special handling in setup
            user.teams.first().team.owned_packages.all().delete()

        response = make_request(
            method=http_verb, url=url, api_client=api_client, data=request_body
        )

        errors = validate_response_against_schema(
            response=response,
            path=path,
            method=http_verb,
            schema=schema,
            resolver=resolver,
        )

        failures.extend(errors)

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
@pytest.mark.parametrize("http_verb", ["put", "patch", "post"])
def test_find_missing_endpoints(api_client, http_verb):
    schema = get_schema(api_client)
    api_paths = extract_paths(schema, "cyberstorm", http_verb)
    failures = []

    for path in api_paths:
        url = convert_path_to_schema_style(path)
        if url not in payload_mapping[http_verb]:
            failures.append(f"Missing test coverage for: {url}")

    if failures:
        pytest.fail("\n".join(failures))
