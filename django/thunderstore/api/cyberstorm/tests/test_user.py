import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
def test_user_delete__when_deleting_own_account__succeeds(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/cyberstorm/current-user/delete/",
        json.dumps({"verification": user.username}),
        content_type="application/json",
    )

    assert response.status_code == 200

    with pytest.raises(User.DoesNotExist) as e:
        User.objects.get(pk=user.pk)
    assert "User matching query does not exist." in str(e.value)


@pytest.mark.django_db
def test_user_delete__when_deleting_own_account__fails_because_user_is_not_authenticated(
    api_client: APIClient,
    user: UserType,
):
    response = api_client.post(
        "/api/cyberstorm/current-user/delete/",
        json.dumps({"verification": user.username}),
        content_type="application/json",
    )

    assert response.status_code == 401
    response_json = response.json()
    assert response_json["detail"] == "Authentication credentials were not provided."
    assert User.objects.filter(pk=user.pk).count() == 1


@pytest.mark.django_db
def test_user_delete__when_missing_verification_parameter__fails(
    api_client: APIClient,
    user: UserType,
):
    api_client.force_authenticate(user)
    response = api_client.post(
        "/api/cyberstorm/current-user/delete/",
        json.dumps({"verification": "TotallyNotCorrectUsername"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    response_json = response.json()
    assert "Invalid verification" in response_json["verification"]
    assert User.objects.filter(pk=user.pk).count() == 1
