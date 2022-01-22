import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.repository.models import Team
from thunderstore.repository.models.namespace import Namespace
from thunderstore.repository.package_upload import PackageUploadForm


@pytest.mark.django_db
def test_package_upload(user, manifest_v1_data, community):

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

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    team = Team.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
        data={
            "team": team.name,
            "communities": [community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.package.owner == team
    assert version.package.namespace == team.get_namespace()
    assert version.package.namespace.name == team.name


@pytest.mark.django_db
def test_package_upload_with_extra_data(user, community, manifest_v1_data):

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

    category = PackageCategory.objects.create(
        name="Test Category",
        slug="test-category",
        community=community,
    )

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    team = Team.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
        data={
            "categories": [category.pk],
            "has_nsfw_content": True,
            "team": team.name,
            "communities": [community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.package.owner == team
    listing = PackageListing.objects.filter(package=version.package).first()
    assert listing.categories.count() == 1
    assert listing.categories.first() == category
    assert listing.has_nsfw_content is True
