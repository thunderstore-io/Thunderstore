import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from thunderstore.repository.models import TeamMember, TeamMemberRole
from thunderstore.repository.package_reference import PackageReference


@pytest.mark.django_db
def test_api_experimental(api_client, active_package_listing):
    # TODO: Create more packages
    with CaptureQueriesContext(connection) as context:
        response = api_client.get(
            "/api/experimental/package/",
        )
    assert len(context) <= 10
    assert response.status_code == 200
    result = response.json()
    assert "next" in result
    assert "previous" in result
    result = result["results"]
    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name


@pytest.mark.django_db
def test_api_experimental_package_detail(api_client, active_package_listing):
    # TODO: Create dependencies and multiple versions
    with CaptureQueriesContext(connection) as context:
        response = api_client.get(
            f"/api/experimental/package/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/",
        )
    assert len(context) <= 10
    assert response.status_code == 200
    result = response.json()
    assert result["namespace"] == active_package_listing.package.namespace.name
    assert result["name"] == active_package_listing.package.name
    assert result["full_name"] == active_package_listing.package.full_package_name


@pytest.mark.django_db
def test_api_experimental_package_version_detail(api_client, package_version):
    # TODO: Create dependencies
    with CaptureQueriesContext(connection) as context:
        response = api_client.get(
            f"/api/experimental/package/"
            f"{package_version.package.namespace.name}/"
            f"{package_version.package.name}/"
            f"{package_version.version_number}/"
        )
    assert response.status_code == 200
    assert len(context) <= 10
    result = response.json()
    assert result["namespace"] == package_version.package.namespace.name
    assert result["name"] == package_version.package.name
    assert result["version_number"] == package_version.version_number
    assert result["full_name"] == package_version.full_version_name


def _create_test_zip(manifest_data) -> bytes:
    icon_raw = io.BytesIO()
    icon = Image.new("RGB", (256, 256), "#FF0000")
    icon.save(icon_raw, format="PNG")

    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(manifest_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    return zip_raw.getvalue()


@pytest.mark.django_db
def test_api_experimental_upload_package_success(
    api_client,
    user,
    manifest_v1_package_bytes,
    package_category,
    team,
    community,
):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.upload"),
        {
            "metadata": json.dumps(
                {
                    "author_name": team.name,
                    "categories": [package_category.slug],
                    "communities": [community.identifier],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes),
        },
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    response = response.json()
    # From manifest_v1_data fixture
    name = "name"
    version = "1.0.0"
    assert PackageReference(team.get_namespace().name, name, version).exists


@pytest.mark.django_db
def test_api_experimental_upload_package_fail_no_permission(
    api_client,
    user,
    manifest_v1_package_bytes,
    package_category,
    team,
    community,
):
    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.upload"),
        {
            "metadata": json.dumps(
                {
                    "author_name": team.name,
                    "categories": [package_category.slug],
                    "communities": [community.identifier],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes),
        },
        HTTP_ACCEPT="application/json",
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {
        "metadata": {"author_name": ["Object with name=Test_Team does not exist."]}
    }
    name = "name"
    version = "1.0.0"
    assert PackageReference(team.get_namespace().name, name, version).exists is False


@pytest.mark.django_db
def test_api_experimental_upload_package_fail_invalid_category(
    api_client,
    user,
    manifest_v1_package_bytes,
    package_category,
    team,
    community,
):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    category_slug = f"invalid-{package_category.slug}"
    response = api_client.post(
        reverse("api:experimental:submission.upload"),
        {
            "metadata": json.dumps(
                {
                    "author_name": team.name,
                    "categories": [category_slug],
                    "communities": [community.identifier],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes),
        },
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 400
    print(response.content)
    assert response.json() == {"metadata": {"categories": {"0": ["Object not found"]}}}
    name = "name"
    version = "1.0.0"
    assert PackageReference(team.get_namespace().name, name, version).exists is False


@pytest.mark.django_db
def test_api_experimental_package_upload_info(
    api_client,
    user,
):
    api_client.force_authenticate(user=user)
    response = api_client.get(
        reverse("api:experimental:submission.upload"),
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert response.json()["max_package_size_bytes"] == 524288000
