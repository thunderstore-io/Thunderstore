import base64
import io
import json
from typing import Any, Dict

import pytest
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.repository.models import TeamMember


@pytest.mark.django_db
def test_experimental_api_validate_readme(
    api_client: APIClient, user: UserType, mocker
) -> None:

    mocked_validator = mocker.patch(
        "thunderstore.repository.api.experimental.views.validators.validate_readme"
    )

    readme = b"# Hello world"

    api_client.force_authenticate(user=user)
    test_data = {"readme_data": base64.b64encode(readme).decode("utf-8")}
    response = api_client.post(
        reverse("api:experimental:submission.validate.readme"),
        data=json.dumps(test_data),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert json.loads(response.content.decode()) == {"success": True}
    mocked_validator.assert_called_with(readme)


@pytest.mark.django_db
def test_experimental_api_validate_manifest(
    api_client: APIClient,
    team_member: TeamMember,
    manifest_v1_data: Dict[str, Any],
    mocker,
) -> None:
    mocked_validator = mocker.patch(
        "thunderstore.repository.api.experimental.views.validators.validate_manifest"
    )

    api_client.force_authenticate(user=team_member.user)
    manifest_data = json.dumps(manifest_v1_data).encode("utf-8")
    test_data = {
        "manifest_data": base64.b64encode(manifest_data).decode("utf-8"),
        "namespace": team_member.team.name,
    }
    response = api_client.post(
        reverse("api:experimental:submission.validate.manifest-v1"),
        data=json.dumps(test_data),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert json.loads(response.content.decode()) == {"success": True}

    mocked_validator.assert_called_with(
        user=team_member.user,
        uploader=team_member.team,
        manifest_data=manifest_data,
    )


@pytest.mark.django_db
def test_experimental_api_validate_icon(api_client: APIClient, user: UserType, mocker):
    mocked_validator = mocker.patch(
        "thunderstore.repository.api.experimental.views.validators.validate_icon"
    )

    api_client.force_authenticate(user=user)
    img = Image.new("RGB", (256, 256), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")

    test_data = {
        "icon_data": base64.b64encode(img_buffer.getvalue()).decode("utf-8"),
    }
    response = api_client.post(
        reverse("api:experimental:submission.validate.icon"),
        data=json.dumps(test_data),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 200
    assert json.loads(response.content.decode()) == {"success": True}
    mocked_validator.assert_called_with(img_buffer.getvalue())
