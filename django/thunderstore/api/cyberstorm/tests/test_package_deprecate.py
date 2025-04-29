import json

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType


def get_deprecate_package_url(listing: PackageListing) -> str:
    namespace_id = listing.package.namespace.name
    package_name = listing.package.name
    return f"/api/cyberstorm/package/{namespace_id}/{package_name}/deprecate/"


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_deprecate_package(
    api_client: APIClient,
    user: UserType,
    active_package_listing: PackageListing,
    user_type: str,
) -> None:

    user = TestUserTypes.get_user_by_type(user_type)

    is_fake_user = user in TestUserTypes.fake_users()
    is_unauthenticated = user_type == TestUserTypes.unauthenticated

    if not is_fake_user and not is_unauthenticated:
        api_client.force_authenticate(user=user)

    data = json.dumps({"deprecate": True})
    url = get_deprecate_package_url(active_package_listing)
    response = api_client.post(url, data=data, content_type="application/json")

    expected_status_code = {
        TestUserTypes.no_user: status.HTTP_401_UNAUTHORIZED,
        TestUserTypes.unauthenticated: status.HTTP_401_UNAUTHORIZED,
        TestUserTypes.regular_user: status.HTTP_403_FORBIDDEN,
        TestUserTypes.deactivated_user: status.HTTP_403_FORBIDDEN,
        TestUserTypes.service_account: status.HTTP_403_FORBIDDEN,
        TestUserTypes.site_admin: status.HTTP_200_OK,
        TestUserTypes.superuser: status.HTTP_200_OK,
    }

    assert response.status_code == expected_status_code[user_type]


@pytest.mark.django_db
def test_deprecate_package_404(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    active_package_listing.package.owner.add_member(user, role="owner")
    api_client.force_authenticate(user=user)
    data = json.dumps({"deprecate": True})
    url = "/api/cyberstorm/package/invalid_namespace/invalid_package/deprecate/"

    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_deprecate_package_invalid_payload(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    active_package_listing.package.owner.add_member(user, role="owner")
    api_client.force_authenticate(user=user)
    data = json.dumps({"deprecate": "invalid_value"})
    url = get_deprecate_package_url(active_package_listing)

    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"deprecate": ["Must be a valid boolean."]}


@pytest.mark.django_db
def test_deprecate_package_required_fields(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    active_package_listing.package.owner.add_member(user, role="owner")
    api_client.force_authenticate(user=user)
    url = get_deprecate_package_url(active_package_listing)

    response = api_client.post(
        url, data=json.dumps({}), content_type="application/json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"deprecate": ["This field is required."]}


@pytest.mark.django_db
def test_deprecate_package_unauthenticated(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    url = get_deprecate_package_url(active_package_listing)
    data = json.dumps({"deprecate": True})
    response = api_client.post(url, data=data, content_type="application/json")
    expect_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == expect_response
