import json
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType

ENSURE_USER_CAN_MANAGE_DEPRECATION_PATH = (
    "thunderstore.repository.models.package.Package.ensure_user_can_manage_deprecation"
)


def get_deprecate_package_url(listing: PackageListing) -> str:
    namespace_id = listing.package.namespace.name
    package_name = listing.package.name
    return f"/api/cyberstorm/package/{namespace_id}/{package_name}/deprecate/"


@pytest.mark.django_db
@pytest.mark.parametrize("is_deprecated", [True, False])
@patch(ENSURE_USER_CAN_MANAGE_DEPRECATION_PATH)
def test_deprecate_package(
    mock_ensure_user_can_manage_deprecation,
    api_client: APIClient,
    user: UserType,
    active_package_listing: PackageListing,
    is_deprecated: bool,
) -> None:
    mock_ensure_user_can_manage_deprecation.return_value = True
    api_client.force_authenticate(user=user)

    data = json.dumps({"deprecate": is_deprecated})
    url = get_deprecate_package_url(active_package_listing)

    response = api_client.post(url, data=data, content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Success"}

    active_package_listing.refresh_from_db()
    assert active_package_listing.package.is_deprecated is is_deprecated


@pytest.mark.django_db
@patch(ENSURE_USER_CAN_MANAGE_DEPRECATION_PATH)
def test_deprecate_package_permission_denied(
    mock_ensure_user_can_manage_deprecation,
    api_client: APIClient,
    active_package_listing: PackageListing,
    user: UserType,
) -> None:
    mock_ensure_user_can_manage_deprecation.return_value = False
    api_client.force_authenticate(user=user)

    data = json.dumps({"deprecate": True})
    url = get_deprecate_package_url(active_package_listing)

    response = api_client.post(url, data=data, content_type="application/json")
    expected_response = {"detail": "You do not have permission to perform this action."}

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == expected_response


@pytest.mark.django_db
def test_deprecate_package_not_authenticated(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    data = json.dumps({"deprecate": True})
    url = get_deprecate_package_url(active_package_listing)

    response = api_client.post(url, data=data, content_type="application/json")
    expected_response = {"detail": "Authentication credentials were not provided."}

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == expected_response
