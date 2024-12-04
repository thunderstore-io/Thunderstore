import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_package_rating_api_view__succeeds(
    api_client: APIClient,
    active_package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/cyberstorm/package/{active_package.namespace}/{active_package.name}/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["state"] == "rated"
    assert actual["score"] == 1

    response = api_client.post(
        f"/api/cyberstorm/package/{active_package.namespace}/{active_package.name}/rate/",
        json.dumps({"target_state": "unrated"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["state"] == "unrated"
    assert actual["score"] == 0


@pytest.mark.django_db
def test_package_rating_api_view__returns_error_for_non_existent_package(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/cyberstorm/package/BAD/BAD/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_package_rating_api_view__returns_error_for_no_user(
    api_client: APIClient,
    active_package: Package,
) -> None:
    response = api_client.post(
        f"/api/cyberstorm/package/{active_package.namespace}/{active_package.name}/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_package_rating_api_view__returns_error_for_bad_data(
    api_client: APIClient,
    active_package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/cyberstorm/package/{active_package.namespace}/{active_package.name}/rate/",
        json.dumps({"bad_data": "rated"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["target_state"] == ["This field is required."]

    response = api_client.post(
        f"/api/cyberstorm/package/{active_package.namespace}/{active_package.name}/rate/",
        json.dumps({"target_state": "bad"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["non_field_errors"] == ["Invalid target_state"]
