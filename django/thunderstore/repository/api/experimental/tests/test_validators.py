import base64

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.core.types import UserType


@pytest.mark.django_db
def test_readme_validation_accepts_valid_markdown(
    api_client: APIClient, user: UserType
):
    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.validate.readme"),
        {"readme_data": base64.b64encode(b"# Test readme").decode("ascii")},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
