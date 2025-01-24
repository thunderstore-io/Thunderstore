from unittest.mock import PropertyMock, patch

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageListing

PERMISSIONS_CHECKER_PATH = (
    "thunderstore.repository.views.package.detail.PermissionsChecker"
)


PERMISSIONS_CHECKER_TEST_PARAMETERS = [
    # ("name_of_the_permissions_function", expected_value)
    # See the PermissionsChecker class in the repository/views/package/detail.py file
    ("can_manage", True),
    ("can_manage", False),
    ("can_manage_deprecation", True),
    ("can_manage_deprecation", False),
    ("can_manage_categories", True),
    ("can_manage_categories", False),
    ("can_deprecate", True),
    ("can_deprecate", False),
    ("can_undeprecate", True),
    ("can_undeprecate", False),
    ("can_unlist", True),
    ("can_unlist", False),
    ("can_moderate", True),
    ("can_moderate", False),
    ("can_view_package_admin_page", True),
    ("can_view_package_admin_page", False),
    ("can_view_listing_admin_page", True),
    ("can_view_listing_admin_page", False),
]


def get_url(namespace_id: str, package_name: str) -> str:
    return f"/api/cyberstorm/package/{namespace_id}/{package_name}/permissions/"


@pytest.mark.django_db
def test_package_permissions_not_logged_in(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    package_name = active_package_listing.package.name
    namespace_id = active_package_listing.package.namespace.name
    url = get_url(namespace_id, package_name)

    response = api_client.get(url, content_type="application/json")
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.django_db
def test_package_permissions_logged_in(
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    package_name = active_package_listing.package.name
    namespace_id = active_package_listing.package.namespace.name
    url = get_url(namespace_id, package_name)

    response = api_client.get(url, content_type="application/json")
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("permissions_func_name", "expected_value"), PERMISSIONS_CHECKER_TEST_PARAMETERS
)
def test_package_permissions_response_values(
    permissions_func_name: str,
    expected_value: bool,
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    """
    Test that the response values are matching the return values of the
    permissions functions in PermissionsChecker.
    """

    api_client.force_authenticate(user)

    package_name = active_package_listing.package.name
    namespace_id = active_package_listing.package.namespace.name
    url = get_url(namespace_id, package_name)

    property_path = f"{PERMISSIONS_CHECKER_PATH}.{permissions_func_name}"
    with patch(property_path, new_callable=PropertyMock) as mock_checker_function:
        mock_checker_function.return_value = expected_value
        response = api_client.get(url, content_type="application/json")

    assert response.status_code == 200
    assert response.json()[permissions_func_name] == expected_value


@pytest.mark.django_db
@patch(f"{PERMISSIONS_CHECKER_PATH}.get_permissions")
def test_package_permissions_not_found(
    mock_get_permissions,
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    mock_get_permissions.return_value = {}

    api_client.force_authenticate(user)

    package_name = active_package_listing.package.name
    namespace_id = active_package_listing.package.namespace.name
    url = get_url(namespace_id, package_name)

    response = api_client.get(url, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"message": "Permissions not found."}
