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
from thunderstore.repository.models.package_version import PackageVersion


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


@pytest.mark.django_db
def test_api_experimental_upload_package(
    api_client,
    user,
    manifest_v1_data,
    package_category,
    uploader_identity,
):
    icon_raw = io.BytesIO()
    icon = Image.new("RGB", (256, 256), "#FF0000")
    icon.save(icon_raw, format="PNG")

    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/experimental/package/version/",
        {
            "author_name": uploader_identity.name,
            "categories": json.dumps([package_category.slug]),
            "has_nsfw_content": True,
            "file": SimpleUploadedFile("mod.zip", zip_raw.getvalue()),
        },
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    response = response.json()
    assert PackageVersion.objects.filter(pk=response["pk"]).exists()
