from typing import List, Optional

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models.community import Community
from thunderstore.repository.factories import PackageVersionFactory


@pytest.mark.django_db
def test_community_is_valid(api_client: APIClient):
    res = send_request(api_client, "noSuchThing", [])

    assert res.status_code == 400


@pytest.mark.django_db
def test_empty_list_passes(api_client: APIClient, community: Community):
    res = send_request(api_client, community.identifier, [])

    assert_validation_errors(res)


@pytest.mark.django_db
def test_valid_packages_pass(api_client: APIClient, community: Community):
    listing1 = PackageListingFactory(community=community)
    listing2 = PackageListingFactory(community=community)

    res = send_request(
        api_client,
        community.identifier,
        [
            listing1.package.latest.full_version_name,
            listing2.package.latest.full_version_name,
        ],
    )

    assert_validation_errors(res)


@pytest.mark.django_db
def test_older_versions_are_valid(api_client: APIClient, community: Community):
    listing = PackageListingFactory(community=community)
    v100 = listing.package.latest
    v101 = PackageVersionFactory(package=listing.package, version_number="1.0.1")
    v123 = PackageVersionFactory(package=listing.package, version_number="1.2.3")

    res = send_request(
        api_client,
        community.identifier,
        [v100.full_version_name, v101.full_version_name, v123.full_version_name],
    )

    assert_validation_errors(res)


@pytest.mark.django_db
def test_all_parts_of_name_are_validated(api_client: APIClient, community: Community):
    listing = PackageListingFactory(community=community)
    team = listing.package.owner.name
    package = listing.package.name
    version = listing.package.latest.version_number

    res = send_request(
        api_client, community.identifier, [f"{team}-{package}-{version}"]
    )
    assert_validation_errors(res)

    res = send_request(api_client, community.identifier, [f"Foo-{package}-{version}"])
    assert_validation_errors(res, "is not listed in")

    res = send_request(api_client, community.identifier, [f"{team}-Foo-{version}"])
    assert_validation_errors(res, "is not listed in")

    res = send_request(api_client, community.identifier, [f"{team}-{package}-1.2.3"])
    assert_validation_errors(res, "is not listed in")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mod", ("Team-Package-1.0", "Team-Package-1.0.0.0", "IsThisTeamOrPackageName-1.0.0")
)
def test_malformed_package_names_cause_errors(
    mod: str, api_client: APIClient, community: Community
):
    res = send_request(api_client, community.identifier, [mod])

    assert_validation_errors(res, f"Invalid package reference string: {mod}")


@pytest.mark.django_db
def test_version_number_is_included(api_client: APIClient, community: Community):
    res = send_request(api_client, community.identifier, ["Team-Package"])

    assert_validation_errors(res, "Missing version number: Team-Package")


@pytest.mark.django_db
def test_package_is_listed_for_community(api_client: APIClient, community: Community):
    listing = PackageListingFactory()  # Creates new community.
    mods = [listing.package.latest.full_version_name]

    res = send_request(api_client, listing.community.identifier, mods)
    assert_validation_errors(res)

    res = send_request(api_client, community.identifier, mods)
    assert_validation_errors(res, f"is not listed in {community.identifier}")


def send_request(
    client: APIClient, community: str, mods: Optional[List[str]] = None
) -> Response:
    return client.get(
        f"/api/experimental/community/{community}/validate-packages/",
        data={"mods": mods or []},
        HTTP_ACCEPT="application/json",
    )


def assert_validation_errors(res: Response, expected: Optional[str] = None) -> None:
    assert res.status_code == 200
    errors = res.json()["validation_errors"]

    if expected:
        assert len(errors) == 1
        assert expected in errors[0]
    else:
        assert len(errors) == 0
