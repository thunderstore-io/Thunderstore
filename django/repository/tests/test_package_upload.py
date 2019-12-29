import io
import json
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from repository.models import UploaderIdentity
from repository.package_upload import PackageUploadForm


@pytest.mark.django_db
def test_package_upload(user, manifest_v1_data):

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

    file_data = {
        "file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())
    }
    identity = UploaderIdentity.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        identity=identity,
        files=file_data,
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.package.owner == identity
