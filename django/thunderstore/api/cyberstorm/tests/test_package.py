import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package
from thunderstore.repository.models.team import TeamMember


@pytest.mark.django_db
def test_package_deprecate_api_view__succeeds(
    api_client: APIClient,
    package: Package,
    team_member: TeamMember,
) -> None:
    api_client.force_authenticate(team_member.user)

    assert Package.objects.get(pk=package.pk).is_deprecated == False

    response = api_client.post(
        f"/api/cyberstorm/package/{package.namespace}/{package.name}/deprecate/",
        json.dumps({"is_deprecated": True}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["is_deprecated"] == True
    assert Package.objects.get(pk=package.pk).is_deprecated == True

    response = api_client.post(
        f"/api/cyberstorm/package/{package.namespace}/{package.name}/deprecate/",
        json.dumps({"is_deprecated": False}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["is_deprecated"] == False
    assert Package.objects.get(pk=package.pk).is_deprecated == False


@pytest.mark.django_db
def test_package_deprecate_api_view__returns_error_for_non_existent_package(
    api_client: APIClient,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/cyberstorm/package/BAD/BAD/deprecate/",
        json.dumps({"is_deprecated": True}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_package_deprecate_api_view__returns_error_for_no_user(
    api_client: APIClient,
) -> None:
    response = api_client.post(
        f"/api/cyberstorm/package/BAD/BAD/deprecate/",
        json.dumps({"is_deprecated": True}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_package_deprecate_api_view__returns_error_for_bad_data(
    api_client: APIClient,
    package: Package,
    user: UserType,
) -> None:
    api_client.force_authenticate(user)
    package.is_active = False
    package.save()

    response = api_client.post(
        f"/api/cyberstorm/package/{package.namespace}/{package.name}/deprecate/",
        json.dumps({"bad_data": True}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["is_deprecated"] == ["This field is required."]

    response = api_client.post(
        f"/api/cyberstorm/package/{package.namespace}/{package.name}/deprecate/",
        json.dumps({"is_deprecated": "bad"}),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["is_deprecated"] == ["Must be a valid boolean."]
