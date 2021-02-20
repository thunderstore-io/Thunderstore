import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from thunderstore.repository.api.experimental.tasks import (
    update_api_experimental_caches,
)
from thunderstore.repository.models import (
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.package_reference import PackageReference


@pytest.mark.django_db
def test_api_experimental(api_client, active_package_listing):
    update_api_experimental_caches()
    response = api_client.get(
        "/api/experimental/package/",
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["package"]["name"] == active_package_listing.package.name
    assert (
        result[0]["package"]["full_name"]
        == active_package_listing.package.full_package_name
    )


def _create_test_zip(manifest_data):
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
    manifest_v1_data,
    package_category,
    uploader_identity,
):
    zip_data = _create_test_zip(manifest_v1_data)

    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/experimental/package/upload/",
        {
            "metadata": json.dumps(
                {
                    "author_name": uploader_identity.name,
                    "categories": [package_category.slug],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", zip_data),
        },
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    response = response.json()
    namespace = uploader_identity.name
    # From manifest_v1_data fixture
    name = "name"
    version = "1.0.0"
    assert PackageReference(namespace, name, version).exists


@pytest.mark.django_db
def test_api_experimental_upload_package_fail_no_permission(
    api_client,
    user,
    manifest_v1_data,
    package_category,
    uploader_identity,
):
    zip_data = _create_test_zip(manifest_v1_data)

    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/experimental/package/upload/",
        {
            "metadata": json.dumps(
                {
                    "author_name": uploader_identity.name,
                    "categories": [package_category.slug],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", zip_data),
        },
        HTTP_ACCEPT="application/json",
    )
    print(response.content)
    assert response.status_code == 400
    assert (
        response.json()["metadata"]["author_name"][0]
        == "Object with name=Test_Identity does not exist."
    )
    namespace = uploader_identity.name
    name = "name"
    version = "1.0.0"
    assert PackageReference(namespace, name, version).exists is False


@pytest.mark.django_db
def test_api_experimental_upload_package_fail_invalid_category(
    api_client,
    user,
    manifest_v1_data,
    package_category,
    uploader_identity,
):
    zip_data = _create_test_zip(manifest_v1_data)

    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    category_slug = f"invalid-{package_category.slug}"
    response = api_client.post(
        "/api/experimental/package/upload/",
        {
            "metadata": json.dumps(
                {
                    "author_name": uploader_identity.name,
                    "categories": [category_slug],
                    "has_nsfw_content": True,
                },
            ),
            "file": SimpleUploadedFile("mod.zip", zip_data),
        },
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 400
    print(response.content)
    assert (
        response.json()["metadata"]["categories"]["invalid-test"]
        == "category not found"
    )
    namespace = uploader_identity.name
    name = "name"
    version = "1.0.0"
    assert PackageReference(namespace, name, version).exists is False
